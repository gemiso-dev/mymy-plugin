"""mymy_login 오케스트레이션 — 선택지 구성 / target 해석 / 핸드오프.

server.py 의 `@mcp.tool mymy_login` 과 CLI(`python -m mymy_mcp.server login`) 가
공통으로 이 모듈의 `login()` 을 호출한다.

동작 분기:
  target 없음                         → 선택지 목록 반환(브라우저 안 엶)
  프리셋명/기존 base_url + 유효 토큰   → 브라우저 없이 active 만 전환(cached)
  신규/토큰 없음/force                 → (임의 URL 이면 MYMY 프로브) → 핸드오프 → 저장·active
"""

from __future__ import annotations

from urllib.parse import urlparse

from . import presets, tokens
from .handoff import browser_handoff
from .probe import probe_mymy


def build_choices() -> dict:
    """무인자 호출 시 선택지 = 코드 프리셋 ∪ 기억 인스턴스. active 표시 + authenticated 플래그."""
    active = tokens.get_active()
    remembered = tokens.list_instances()
    choices: list[dict] = []
    seen: set[str] = set()

    for p in presets.PRESETS:
        base = p["base_url"].rstrip("/")
        seen.add(base)
        choices.append(
            {
                "name": p["name"],
                "base_url": base,
                "web_url": p["web_url"].rstrip("/"),
                "authenticated": bool(tokens.token_for(base)),
            }
        )

    for base, inst in remembered.items():
        if base in seen:
            continue
        seen.add(base)
        choices.append(
            {
                "name": inst.get("name"),
                "base_url": base,
                "web_url": (inst.get("web_url") or base),
                "authenticated": bool(inst.get("access")),
            }
        )

    return {
        "needs_selection": True,
        "active": active,
        "choices": choices,
        "hint": (
            "연결할 인스턴스를 고르세요. 프리셋명(local/docker/koba) 또는 URL 로 "
            "mymy_login 을 다시 호출하세요."
        ),
    }


def match_known(target: str) -> dict | None:
    """프리셋명 / 프리셋 base_url / 기억된 base_url 과 매칭 → {name, base_url, web_url}. 없으면 None."""
    t = target.strip()

    p = presets.preset_by_name(t) or presets.preset_by_base(t)
    if p:
        return {"name": p["name"], "base_url": p["base_url"].rstrip("/"), "web_url": p["web_url"].rstrip("/")}

    norm = t.rstrip("/")
    inst = tokens.load_instance(norm)
    if inst:
        return {"name": inst.get("name"), "base_url": norm, "web_url": (inst.get("web_url") or norm)}

    return None


def validate_url(target: str) -> str | None:
    """임의 URL 검증 — http/https scheme + netloc 필수. 정규화된 URL 또는 None."""
    parsed = urlparse(target.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return target.strip().rstrip("/")


def _handoff_and_save(base_url: str, web_url: str, name: str | None) -> dict:
    handoff = browser_handoff(web_url)
    tokens.save_instance(base_url, handoff["access"], web_url=web_url, name=name)
    return {
        "logged_in": True,
        "base_url": base_url,
        "web_url": web_url,
        "method": "browser-handoff",
    }


def login(target: str | None = None, force: bool = False) -> dict:
    tokens.migrate_v1_if_needed()

    if target is None:
        return build_choices()

    known = match_known(target)
    if known:
        base, web = known["base_url"], known["web_url"]
        if not force and tokens.token_for(base):
            tokens.set_active(base)
            return {"switched": True, "base_url": base, "cached": True}
        # 프리셋/기억 인스턴스는 신뢰 대상 → 프로브 생략, 바로 핸드오프
        return _handoff_and_save(base, web, name=known.get("name"))

    # 임의 URL 경로
    base = validate_url(target)
    if base is None:
        return {
            "error": "invalid_url",
            "target": target,
            "message": "http/https URL 또는 프리셋명(local/docker/koba)이어야 합니다.",
        }
    if not probe_mymy(base):
        return {
            "error": "not_mymy",
            "base_url": base,
            "message": (
                f"{base} 는 MYMY 서버로 확인되지 않았습니다 (/llms.txt 프로브 실패). "
                "브라우저를 열지 않았습니다."
            ),
        }
    # prod 단일 오리진 가정: base == web
    return _handoff_and_save(base, base, name=None)
