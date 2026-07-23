"""MYMY MCP 로컬 프록시 서버 (stdio).

두 가지를 노출한다:
  1. `mymy_login` 도구/프롬프트 — 브라우저 핸드오프로 mym_ 토큰을 발급받아 로컬 저장(항상 사용 가능).
     연결 대상은 인자로 선택/전환할 수 있고(멀티 인스턴스), 무인자 호출 시 선택지를 반환한다.
  2. MYMY 서버 `/api/mcp` 의 **모든 도구를 투명 프록시** — 서버 도구 카탈로그가 단일 진실원이라
     서버에 도구가 추가돼도 이 플러그인은 무변경(재정의하지 않음).

업스트림 프록시는 **동적 client_factory** 로 마운트한다. FastMCPProxy 는 요청마다
client_factory() 를 호출하므로, active 인스턴스가 바뀌면 프로세스 재시작 없이 그 서버로
프록시된다(make_transport 가 매 호출 active 의 {base}/api/mcp 로 새 transport 생성).

Claude Code(플러그인 `.mcp.json`)와 Claude Desktop(`claude_desktop_config.json`) 양쪽에서
동일한 stdio 서버로 동작한다. Desktop은 `@mcp.prompt` 를 "+" 메뉴로 노출한다.
"""

from __future__ import annotations

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.providers.proxy import FastMCPProxy, ProxyClient

from . import login as login_mod
from .client import make_transport

load_dotenv()

# 로컬 도구/프롬프트를 소유하는 메인 서버. 업스트림 프록시는 mount 로 합성한다.
# (login 을 로컬에 두면 미인증 상태에서 tools/list 시 업스트림이 401 이어도
#  mymy_login 은 항상 나열되어 사용자가 로그인할 수 있다.)
mcp = FastMCP("mymy")


@mcp.tool
def mymy_login(target: str | None = None, force: bool = False) -> dict:
    """MYMY 인스턴스에 브라우저 핸드오프로 로그인하거나, 인증된 인스턴스로 전환한다.

    - 인자 없이 호출: 연결 가능한 인스턴스 선택지를 반환한다(브라우저를 열지 않음).
      사용자에게 어디로 연결할지 물어본 뒤, 고른 값으로 `mymy_login("<이름 또는 URL>")` 재호출.
    - `target` = 프리셋명(local/koba) 또는 이미 로그인한 base_url + 유효 토큰:
      브라우저 없이 active 만 전환한다(cached).
    - `target` = 신규 URL / 토큰 없음 / `force=True`: 브라우저 창이 열리면 MYMY 웹에
      로그인(이미 로그인 상태면 생략) 후 '연결 허용'을 누른다. 발급된 토큰은
      ~/.mymy-mcp/credentials.json 에 인스턴스별로 저장되어 이후 세션에서 재사용된다.

    신규 임의 URL 은 브라우저를 열기 전에 `GET <url>/llms.txt` 로 MYMY 서버인지 검증한다.
    """
    return login_mod.login(target, force)


@mcp.prompt
def mymy_login_prompt() -> str:
    """MYMY 브라우저 핸드오프 인증/재인증."""
    return (
        "`mymy_login` 도구를 호출해 MYMY 인증을 실행하세요. 특정 인스턴스로 바로 가려면 "
        "`mymy_login(\"local\")` 처럼 프리셋명이나 URL 을 넘기고, 어디로 연결할지 먼저 고르려면 "
        "인자 없이 호출해 반환된 선택지를 사용자에게 제시한 뒤 다시 호출하세요. "
        "브라우저 창이 열리면 MYMY 웹에 로그인(이미 로그인 상태면 생략) 후 '연결 허용'을 누릅니다. "
        "완료되면 인증 성공 여부와 base_url 을 보고하세요. "
        "인증은 사용자 PC 단위로 인스턴스별 저장되며, 만료(90일)/철회 시에만 다시 실행하면 됩니다."
    )


# 업스트림 MYMY /api/mcp 의 전 도구를 투명 프록시로 합성(prefix 없이 병합).
# 매 요청 _client_factory() → make_transport() 가 active 인스턴스의 {base}/api/mcp 로
# 새 transport 를 만들고, MymAuth 가 그 인스턴스의 최신 mym_ 토큰을 주입한다.
def _client_factory() -> ProxyClient:
    return ProxyClient(make_transport())


_upstream = FastMCPProxy(client_factory=_client_factory, name="mymy-upstream")
mcp.mount(_upstream)


def main() -> None:
    import sys

    argv = sys.argv[1:]
    # CLI 편의: `python -m mymy_mcp.server login [target]` 로 핸드오프/전환만 실행(테스트/수동 인증).
    # target 생략 시 dev 기본(local 프리셋)으로 로그인.
    if argv and argv[0] == "login":
        target = argv[1] if len(argv) > 1 else "local"
        result = login_mod.login(target)
        print(result)
        return
    mcp.run()


if __name__ == "__main__":
    main()
