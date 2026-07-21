"""프록시 통합 테스트 — 인-프로세스 업스트림 MCP 서버(HTTP)를 띄우고,
플러그인의 create_proxy + mount + MymAuth 조합이

  1. 업스트림 도구(`ping`)를 tools/list 로 노출하고(투명 프록시),
  2. tools/call 을 업스트림으로 포워딩하며,
  3. 요청에 저장된 mym_ 토큰을 Authorization 헤더로 주입한다

는 것을 실제 HTTP 왕복으로 검증한다. (설계 문서 §11 "투명 프록시 PoC" 리스크 클로징)

mymy-v4 전체 스택 없이 FastMCP 업스트림 스텁만으로 프록시 배선을 검증한다.
"""

from __future__ import annotations

import asyncio
import socket
import threading
import time

import uvicorn
from fastmcp import Client, FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server import create_proxy
from fastmcp.server.dependencies import get_http_headers

from mymy_mcp import tokens
from mymy_mcp.client import MymAuth


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_port(port: int, timeout: float = 15.0) -> None:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise TimeoutError(f"upstream did not start on port {port}")


def _build_upstream_app(captured: dict, path: str):
    up = FastMCP("upstream-stub")

    @up.tool
    def ping() -> dict:
        """업스트림 스텁 도구 — 수신 Authorization 헤더를 캡처하고 pong 반환.

        get_http_headers 는 기본적으로 authorization 을 제외하므로 include 로 명시 요청한다
        (실서버 /api/mcp 는 Express 미들웨어로 헤더를 읽어 이 필터와 무관).
        """
        headers = get_http_headers(include={"authorization"})
        captured["auth"] = headers.get("authorization")
        return {"pong": True}

    # stateless_http=True → mymy-v4 /api/mcp 와 동일 모드. host_origin_protection
    # 끄기 → 테스트 loopback 요청이 origin 가드에 걸리지 않게.
    return up.http_app(path=path, stateless_http=True, host_origin_protection=False)


def test_proxy_forwards_call_and_injects_token(monkeypatch):
    # Arrange — 저장 토큰(주입 소스)
    monkeypatch.setattr(tokens, "load_token", lambda: "mym_testtoken")
    captured: dict = {}
    port = _free_port()
    url = f"http://127.0.0.1:{port}/api/mcp"

    app = _build_upstream_app(captured, "/api/mcp")
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: asyncio.run(server.serve()), daemon=True)
    thread.start()
    try:
        _wait_port(port)

        async def scenario():
            # 플러그인과 동일한 배선: create_proxy(transport) 를 로컬 서버에 mount
            transport = StreamableHttpTransport(url=url, auth=MymAuth())
            proxy = create_proxy(transport, name="upstream-proxy")
            composed = FastMCP("mymy-test")

            @composed.tool
            def mymy_login() -> dict:  # 로컬 도구(항상 노출)
                return {"logged_in": False}

            composed.mount(proxy)

            async with Client(composed) as c:
                names = {t.name for t in await c.list_tools()}
                result = await c.call_tool("ping", {})
                return names, result

        names, result = asyncio.run(asyncio.wait_for(scenario(), timeout=30))

        # Assert — 로컬 + 프록시 도구 병합 노출
        assert "mymy_login" in names, f"local tool missing: {names}"
        assert "ping" in names, f"proxied upstream tool missing: {names}"
        # 포워딩 결과
        assert result.data == {"pong": True}
        # 토큰 주입(요청마다 최신 토큰 → Bearer)
        assert captured.get("auth") == "Bearer mym_testtoken"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
