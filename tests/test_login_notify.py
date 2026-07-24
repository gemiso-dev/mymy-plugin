"""mymy_login 성공 시 tools/list_changed 통지 검증.

active 인스턴스가 바뀌면 upstream(/api/mcp) 도구 카탈로그가 달라지므로, 서버는
클라이언트가 재시작 없이 tools/list 를 다시 받아오도록 tools/list_changed 를 보내야
한다(README/설계 §"재시작 없이 도구 노출"). 선택지 조회(무인자)나 에러에서는 active 가
바뀌지 않으므로 통지하지 않는다.
"""

from __future__ import annotations

import asyncio

from mymy_mcp import server


def _raw_tool():
    """mcp.tool 로 감싼 mymy_login 의 원본 async 함수(FunctionTool.fn)."""
    return getattr(server.mymy_login, "fn", server.mymy_login)


class _FakeSession:
    def __init__(self) -> None:
        self.calls = 0

    async def send_tool_list_changed(self) -> None:
        self.calls += 1


def _patch(monkeypatch, login_result: dict) -> _FakeSession:
    session = _FakeSession()

    class _FakeCtx:
        pass

    ctx = _FakeCtx()
    ctx.session = session

    monkeypatch.setattr(server, "get_context", lambda: ctx)
    monkeypatch.setattr(server.login_mod, "login", lambda target, force: login_result)
    return session


def test_switch_emits_list_changed(monkeypatch):
    session = _patch(monkeypatch, {"switched": True, "base_url": "http://x", "cached": True})
    result = asyncio.run(_raw_tool()(target="koba", force=False))
    assert result["switched"] is True
    assert session.calls == 1, "전환 성공 시 tools/list_changed 를 1회 보내야 한다"


def test_handoff_login_emits_list_changed(monkeypatch):
    session = _patch(monkeypatch, {"logged_in": True, "base_url": "http://x", "method": "browser-handoff"})
    result = asyncio.run(_raw_tool()(target="http://new-mymy", force=False))
    assert result["logged_in"] is True
    assert session.calls == 1, "핸드오프 로그인 성공 시 tools/list_changed 를 보내야 한다"


def test_choices_listing_does_not_emit(monkeypatch):
    session = _patch(monkeypatch, {"needs_selection": True, "choices": []})
    result = asyncio.run(_raw_tool()(target=None, force=False))
    assert result["needs_selection"] is True
    assert session.calls == 0, "선택지 조회는 active 를 바꾸지 않으므로 통지하지 않는다"


def test_error_result_does_not_emit(monkeypatch):
    session = _patch(monkeypatch, {"error": "not_mymy", "base_url": "http://x"})
    result = asyncio.run(_raw_tool()(target="http://not-mymy", force=False))
    assert result["error"] == "not_mymy"
    assert session.calls == 0, "에러 결과는 통지하지 않는다"


def test_notify_failure_does_not_break_login(monkeypatch):
    """클라이언트가 list_changed 미지원이어도 로그인 결과는 그대로 반환된다."""

    class _BoomSession:
        async def send_tool_list_changed(self) -> None:
            raise RuntimeError("client does not support notifications")

    class _FakeCtx:
        pass

    ctx = _FakeCtx()
    ctx.session = _BoomSession()
    monkeypatch.setattr(server, "get_context", lambda: ctx)
    monkeypatch.setattr(
        server.login_mod, "login", lambda target, force: {"switched": True, "base_url": "http://x"}
    )

    result = asyncio.run(_raw_tool()(target="koba", force=False))
    assert result["switched"] is True  # 통지 실패가 로그인 결과를 깨지 않는다
