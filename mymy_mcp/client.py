"""MYMY /api/mcp 로 향하는 프록시 전송(transport) 구성.

핵심: 인증 토큰은 **요청마다 동적으로** credentials.json에서 읽어 주입한다.
StreamableHttpTransport는 생성 시점에 헤더가 고정되지만, httpx.Auth 를 쓰면 매 요청마다
최신 토큰을 붙일 수 있어 /mymy-login 이후 서버 재시작 없이 토큰이 반영된다.
토큰이 없거나 만료(401)면 상위(server.py)가 재로그인을 안내한다.
"""

from __future__ import annotations

from collections.abc import Generator

import httpx
from fastmcp.client.transports import StreamableHttpTransport

from . import tokens


def current_base_url() -> str:
    """API base_url — active 인스턴스 > dev 기본.

    로그인(active 인스턴스)이 아직 없으면 dev 기본으로 폴백한다. 이 상태의 도구
    호출은 토큰이 없어 401 이 되고, 상위(server.py)가 재로그인을 안내한다.
    대상 서버는 env 가 아니라 mymy_login 인자(프리셋/URL)로 결정된다.
    """
    return (tokens.get_active() or "http://localhost:4000").rstrip("/")


class MymAuth(httpx.Auth):
    """요청마다 저장된 mym_ 토큰을 Authorization 헤더로 주입한다."""

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        token = tokens.load_token()
        if token:
            request.headers["Authorization"] = f"Bearer {token}"
        yield request


def make_transport() -> StreamableHttpTransport:
    """MYMY MCP 엔드포인트로 향하는 동적 인증 transport."""
    url = f"{current_base_url()}/api/mcp"
    return StreamableHttpTransport(url=url, auth=MymAuth())
