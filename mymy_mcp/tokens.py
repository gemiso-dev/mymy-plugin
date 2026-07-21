"""MYMY mym_ API 토큰의 로컬 저장.

~/.mymy-mcp/credentials.json 구조:
    { "access": "mym_...", "base_url": "http://localhost:4000" }

MYMY MCP는 GDC 같은 워크스페이스/프로젝트 컨텍스트가 없어(카테고리 권한은 서버가 토큰으로
판정) 사용자 단위 단일 토큰만 저장한다(D9). mym_ 토큰은 refresh 회전이 없으므로(90일 만료)
access 하나만 보관하고, 만료/철회로 401이 나면 재로그인한다.

POSIX는 0600. Windows는 사용자 프로필 ACL에 의존(시크릿 커밋·로그 노출 금지).
"""

from __future__ import annotations

import json
import os
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


def load_token() -> str | None:
    """저장된 mym_ 토큰을 반환한다. 없으면 None."""
    return _read().get("access") or None


def load_base_url() -> str | None:
    """저장된 인증 서버 base_url(있으면). env 미설정 시 fallback."""
    return _read().get("base_url") or None


def save_token(access: str, base_url: str) -> None:
    _write({"access": access, "base_url": base_url})


def clear_token() -> None:
    _cred_path().unlink(missing_ok=True)
