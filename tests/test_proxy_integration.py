"""프록시 통합 테스트 — 인-프로세스 업스트림 MCP 서버(HTTP)를 띄우고,
플러그인의 **동적 프록시**(FastMCPProxy + client_factory) + MymAuth 조합이

  1. 업스트림 도구를 tools/list 로 노출하고(투명 프록시),
  2. tools/call 을 업스트림으로 포워딩하며,
  3. 요청에 active 인스턴스의 mym_ 토큰을 Authorization 헤더로 주입하고,
  4. **active 를 바꾸면 프로세스 재시작 없이** 다른 업스트림으로 프록시된다

는 것을 실제 HTTP 왕복으로 검증한다. (설계 §"핵심 발견 — 런타임 전환이 실제로 가능")

mymy-v4 전체 스택 없이 FastMCP 업스트림 스텁만으로 프록시 배선을 검증한다.
"""

from __future__ import annotations

import asyncio
import socket
import threading
import time
from contextlib import contextmanager

import uvicorn
from fastmcp import Client, FastMCP
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.providers.proxy import FastMCPProxy, ProxyClient

from mymy_mcp import tokens
from mymy_mcp.client import make_transport


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


def _build_upstream_app(captured: dict, whoami: str):
    up = FastMCP(f"upstream-{whoami}")

    @up.tool
    def ping() -> dict:
        """수신 Authorization 헤더를 캡처하고 서버 식별자를 반환."""
        headers = get_http_headers(include={"authorization"})
        captured["auth"] = headers.get("authorization")
        return {"pong": True, "whoami": whoami}

    return up.http_app(path="/api/mcp", stateless_http=True, host_origin_protection=False)


@contextmanager
def _serve(app, port: int):
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: asyncio.run(server.serve()), daemon=True)
    thread.start()
    try:
        _wait_port(port)
        yield
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def _client_factory() -> ProxyClient:
    # server.py 와 동일한 배선: 매 호출 active 인스턴스로 새 transport
    return ProxyClient(make_transport())


def test_proxy_forwards_call_and_injects_token(tmp_path, monkeypatch):
    # Arrange — tokens 격리 + active 인스턴스(주입 소스)
    cred = tmp_path / "credentials.json"
    monkeypatch.setattr(tokens, "_cred_path", lambda: cred)
    monkeypatch.delenv("MYMY_BASE_URL", raising=False)

    captured: dict = {}
    port = _free_port()
    tokens.save_instance(f"http://127.0.0.1:{port}", "mym_testtoken", f"http://127.0.0.1:{port}", "t")

    with _serve(_build_upstream_app(captured, "A"), port):

        async def scenario():
            proxy = FastMCPProxy(client_factory=_client_factory, name="upstream-proxy")
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

        assert "mymy_login" in names, f"local tool missing: {names}"
        assert "ping" in names, f"proxied upstream tool missing: {names}"
        assert result.data == {"pong": True, "whoami": "A"}
        assert captured.get("auth") == "Bearer mym_testtoken"


def test_active_switch_reroutes_without_restart(tmp_path, monkeypatch):
    # 두 업스트림 A/B 를 동시에 띄우고, active 포인터만 바꿔 같은 프록시가
    # 재시작 없이 다른 서버로 라우팅됨을 실측한다.
    cred = tmp_path / "credentials.json"
    monkeypatch.setattr(tokens, "_cred_path", lambda: cred)
    monkeypatch.delenv("MYMY_BASE_URL", raising=False)

    cap_a: dict = {}
    cap_b: dict = {}
    port_a, port_b = _free_port(), _free_port()
    base_a, base_b = f"http://127.0.0.1:{port_a}", f"http://127.0.0.1:{port_b}"
    tokens.save_instance(base_a, "mym_a", base_a, "A")
    tokens.save_instance(base_b, "mym_b", base_b, "B")  # save_instance → active = B

    with _serve(_build_upstream_app(cap_a, "A"), port_a), _serve(_build_upstream_app(cap_b, "B"), port_b):

        async def call_once():
            proxy = FastMCPProxy(client_factory=_client_factory, name="p")
            composed = FastMCP("mymy-test")
            composed.mount(proxy)
            async with Client(composed) as c:
                return (await c.call_tool("ping", {})).data

        # active = A → A 로 라우팅 + A 토큰 주입
        tokens.set_active(base_a)
        data_a = asyncio.run(asyncio.wait_for(call_once(), timeout=30))
        assert data_a["whoami"] == "A"
        assert cap_a.get("auth") == "Bearer mym_a"

        # active = B → 재시작 없이 B 로 라우팅 + B 토큰 주입
        tokens.set_active(base_b)
        data_b = asyncio.run(asyncio.wait_for(call_once(), timeout=30))
        assert data_b["whoami"] == "B"
        assert cap_b.get("auth") == "Bearer mym_b"
