"""MYMY mym_ API 토큰의 로컬 저장 (v2 멀티 인스턴스).

~/.mymy-mcp/credentials.json 구조 (v2):
    {
      "version": 2,
      "active": "http://localhost:4000",
      "instances": {
        "http://localhost:4000": {
          "access": "mym_...", "web_url": "http://localhost:3000",
          "name": "local", "last_login": 1690000000000
        }
      }
    }

- 키 = 정규화된 base_url(끝 `/` 제거). 인스턴스마다 자기 토큰을 보관 → 이미 로그인한
  서버로 전환은 재로그인 없이 즉시 가능(active 포인터만 이동).
- 구 포맷 `{access, base_url}`(v1)은 최초 접근 시 v2로 무손실 승격한다(migrate_v1_if_needed).
- mym_ 토큰은 refresh 회전이 없으므로(90일 만료) access 하나만 보관하고, 만료/철회로 401이
  나면 재로그인한다.

POSIX는 0600. Windows는 사용자 프로필 ACL에 의존(시크릿 커밋·로그 노출 금지).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


def _cred_path() -> Path:
    return Path.home() / ".mymy-mcp" / "credentials.json"


def _read() -> dict:
    path = _cred_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def _write(data: dict) -> None:
    path = _cred_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    if os.name == "posix":
        os.chmod(path, 0o600)


def _normalize(base_url: str) -> str:
    """인스턴스 키 정규화 — 끝 `/` 제거."""
    return base_url.rstrip("/")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _empty_v2() -> dict:
    return {"version": 2, "active": None, "instances": {}}


def _migrate_v1(data: dict) -> dict:
    """v1 `{access, base_url}` → v2 구조로 변환(디스크 기록 없음)."""
    access = data.get("access")
    base = data.get("base_url")
    if not access or not base:
        return _empty_v2()
    base = _normalize(base)
    web = base  # v1 은 web_url 을 저장하지 않았으므로 base 로 폴백(로그인 후 재핸드오프 시 갱신)
    return {
        "version": 2,
        "active": base,
        "instances": {
            base: {
                "access": access,
                "web_url": _normalize(web),
                "name": None,
                "last_login": None,
            }
        },
    }


def _load_v2() -> dict:
    """creds 를 v2 구조로 읽는다(v1은 메모리상 승격). 파일 부재/손상 시 빈 v2."""
    data = _read()
    if not data:
        return _empty_v2()
    if data.get("version") == 2:
        data.setdefault("active", None)
        data.setdefault("instances", {})
        return data
    return _migrate_v1(data)


# --- 멀티 인스턴스 API ----------------------------------------------------------

def migrate_v1_if_needed() -> bool:
    """디스크의 v1 파일을 발견하면 v2로 승격 기록한다. 승격 시 True."""
    data = _read()
    if data and data.get("version") != 2 and (data.get("access") or data.get("base_url")):
        _write(_migrate_v1(data))
        return True
    return False


def get_active() -> str | None:
    """현재 프록시가 향하는 인스턴스의 base_url(없으면 None)."""
    return _load_v2().get("active")


def set_active(base_url: str) -> None:
    """active 포인터를 이동한다(토큰 발급 없이 전환)."""
    data = _load_v2()
    data["active"] = _normalize(base_url)
    _write(data)


def save_instance(
    base_url: str,
    access: str,
    web_url: str | None = None,
    name: str | None = None,
) -> None:
    """인스턴스 토큰을 저장하고 active 로 설정한다."""
    base = _normalize(base_url)
    data = _load_v2()
    data["instances"][base] = {
        "access": access,
        "web_url": _normalize(web_url) if web_url else base,
        "name": name,
        "last_login": _now_ms(),
    }
    data["active"] = base
    _write(data)


def load_instance(base_url: str) -> dict | None:
    """base_url 로 기억된 인스턴스 정보(없으면 None)."""
    return _load_v2()["instances"].get(_normalize(base_url))


def list_instances() -> dict:
    """기억된 인스턴스 전체 `{base_url: {...}}`."""
    return _load_v2()["instances"]


def token_for(base_url: str | None) -> str | None:
    """특정 인스턴스의 mym_ 토큰(없으면 None)."""
    if not base_url:
        return None
    inst = load_instance(base_url)
    return (inst or {}).get("access") or None


# --- 하위호환 표면(active 인스턴스 기준) ---------------------------------------

def load_token() -> str | None:
    """active 인스턴스의 mym_ 토큰을 반환한다(없으면 None)."""
    return token_for(get_active())


def load_base_url() -> str | None:
    """active 인스턴스의 base_url(없으면 None). env 미설정 시 fallback."""
    return get_active()


def save_token(access: str, base_url: str) -> None:
    """v1 호환 진입점 — 단일 인스턴스 저장(web_url = base_url)."""
    save_instance(base_url, access, web_url=base_url)


def clear_token() -> None:
    """모든 인스턴스/토큰 삭제(파일 제거)."""
    _cred_path().unlink(missing_ok=True)
