"""MYMY MCP 로컬 프록시 서버 (stdio).

두 가지를 노출한다:
  1. `mymy_login` 도구/프롬프트 — 브라우저 핸드오프로 mym_ 토큰을 발급받아 로컬 저장(항상 사용 가능).
  2. MYMY 서버 `/api/mcp` 의 **모든 도구를 투명 프록시** — 서버 도구 카탈로그가 단일 진실원이라
     서버에 도구가 추가돼도 이 플러그인은 무변경(재정의하지 않음).

Claude Code(플러그인 `.mcp.json`)와 Claude Desktop(`claude_desktop_config.json`) 양쪽에서
동일한 stdio 서버로 동작한다. Desktop은 `@mcp.prompt` 를 "+" 메뉴로 노출한다.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server import create_proxy

from . import tokens
from .client import current_base_url, make_transport
from .handoff import browser_handoff

load_dotenv()

_WEB_URL = os.environ.get("MYMY_WEB_URL", "http://localhost:3000").rstrip("/")

# 로컬 도구/프롬프트를 소유하는 메인 서버. 업스트림 프록시는 mount 로 합성한다.
# (login 을 로컬에 두면 미인증 상태에서 tools/list 시 업스트림이 401 이어도
#  mymy_login 은 항상 나열되어 사용자가 로그인할 수 있다.)
mcp = FastMCP("mymy")


@mcp.tool
def mymy_login() -> dict:
    """브라우저 핸드오프로 MYMY MCP 전용 mym_ 토큰을 발급받아 로컬에 저장한다.

    브라우저 창이 열리면 평소처럼 MYMY 웹에 로그인(이미 로그인돼 있으면 생략)한 뒤
    '연결 허용'을 누른다. 발급된 토큰은 ~/.mymy-mcp/credentials.json 에 저장되어
    이후 세션에서 재사용된다(만료/철회 시 재로그인).
    """
    base = current_base_url()
    handoff = browser_handoff(_WEB_URL)
    tokens.save_token(handoff["access"], base)
    return {
        "logged_in": True,
        "base_url": base,
        "method": "browser-handoff",
    }


@mcp.prompt
def mymy_login_prompt() -> str:
    """MYMY 브라우저 핸드오프 인증/재인증."""
    return (
        "`mymy_login` 도구를 호출해 브라우저 핸드오프 인증을 실행하세요. "
        "브라우저 창이 열리면 MYMY 웹에 로그인(이미 로그인 상태면 생략) 후 '연결 허용'을 누릅니다. "
        "완료되면 인증 성공 여부와 base_url 을 보고하세요. "
        "인증은 사용자 PC 단위로 저장되며, 만료(90일)/철회 시에만 다시 실행하면 됩니다."
    )


# 업스트림 MYMY /api/mcp 의 전 도구를 투명 프록시로 합성(prefix 없이 병합).
# create_proxy 는 transport 를 직접 받아 매 요청 새 세션으로 업스트림에 연결한다
# (make_transport 의 httpx.Auth 가 요청마다 최신 mym_ 토큰을 주입).
_upstream = create_proxy(make_transport(), name="mymy-upstream")
mcp.mount(_upstream)


def main() -> None:
    import sys

    argv = sys.argv[1:]
    # CLI 편의: `python -m mymy_mcp.server login` 로 핸드오프만 실행(테스트/수동 인증).
    if argv and argv[0] == "login":
        base = current_base_url()
        handoff = browser_handoff(_WEB_URL)
        tokens.save_token(handoff["access"], base)
        print(f"authenticated (base_url={base})")
        return
    mcp.run()


if __name__ == "__main__":
    main()
