"""MYMY 대상 프로브 단위 테스트 (Validation/External).

케이스 분류: Validation(마커 판정) / External(HTTP 상태·실패).
네트워크는 fetch_llms_txt 를 monkeypatch 로 대체.
"""

from __future__ import annotations

from mymy_mcp import probe

# 실제 apps/server/src/routes/llmsTxt.ts 본문을 대표하는 샘플(혼합 대소문자 "MyMy").
REAL_LLMS_TXT = """# MyMy — Content Management System

> MyMy is a self-hosted CMS ... a Model Context
> Protocol (MCP) endpoint that AI agents can use with an `mym_` API token.

## API & Integration
- [MCP endpoint](http://x/api/mcp): Model Context Protocol over Streamable HTTP (stateless); POST only

## MCP tools
- search_contents: ...
"""


# --- has_mymy_markers: 구조 마커 판정 ------------------------------------------

def test_real_body_passes():
    assert probe.has_mymy_markers(REAL_LLMS_TXT) is True


def test_mixed_case_mymy_regression():
    # 회귀 가드: 실서버는 "MyMy"(혼합)를 쓴다 — 대문자 "MYMY" 매칭 실수 방지.
    # 브랜드 문자열을 아예 안 보므로 "MyMy" 본문이 정상 통과해야 한다.
    assert "MYMY" not in REAL_LLMS_TXT  # 실서버엔 대문자 MYMY 없음
    assert probe.has_mymy_markers(REAL_LLMS_TXT) is True


def test_header_marker_only_passes():
    body = "random preamble\n[endpoint](http://x/api/mcp)\n## MCP tools\n- foo"
    assert probe.has_mymy_markers(body) is True


def test_no_markers_fails():
    assert probe.has_mymy_markers("hello world, nothing here") is False


def test_brand_only_without_structure_fails():
    # 브랜드 "MYMY" 만 있고 구조 마커(/api/mcp)가 없으면 거부 — 브랜드 위조 방어.
    assert probe.has_mymy_markers("# MYMY\nModel Context Protocol") is False


def test_api_mcp_without_mcp_phrase_fails():
    assert probe.has_mymy_markers("see /api/mcp for details") is False


# --- probe_mymy: HTTP 상태 결합 ------------------------------------------------

def test_probe_200_with_markers_true(monkeypatch):
    monkeypatch.setattr(probe, "fetch_llms_txt", lambda base: (200, REAL_LLMS_TXT))
    assert probe.probe_mymy("http://new-mymy:4000") is True


def test_probe_200_no_markers_false(monkeypatch):
    monkeypatch.setattr(probe, "fetch_llms_txt", lambda base: (200, "not mymy"))
    assert probe.probe_mymy("http://evil:4000") is False


def test_probe_404_false(monkeypatch):
    monkeypatch.setattr(probe, "fetch_llms_txt", lambda base: (404, ""))
    assert probe.probe_mymy("http://x:4000") is False


def test_probe_network_failure_false(monkeypatch):
    monkeypatch.setattr(probe, "fetch_llms_txt", lambda base: None)
    assert probe.probe_mymy("http://timeout:4000") is False
