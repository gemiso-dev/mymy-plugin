"""mymy-mcp 단위 테스트 — 네트워크 불필요 부분(토큰 저장/로드, 콜백 파싱, 인증 주입)."""

from __future__ import annotations

import httpx

from mymy_mcp import client, tokens
from mymy_mcp.handoff import _parse_body


# --- tokens: 저장/로드/철회 라운드트립 ------------------------------------------

def test_token_roundtrip(tmp_path, monkeypatch):
    cred = tmp_path / "credentials.json"
    monkeypatch.setattr(tokens, "_cred_path", lambda: cred)

    assert tokens.load_token() is None  # 파일 없음
    tokens.save_token("mym_abc", "http://localhost:4000")
    assert tokens.load_token() == "mym_abc"
    assert tokens.load_base_url() == "http://localhost:4000"
    tokens.clear_token()
    assert tokens.load_token() is None


def test_load_token_corrupt_file(tmp_path, monkeypatch):
    cred = tmp_path / "credentials.json"
    cred.write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(tokens, "_cred_path", lambda: cred)
    assert tokens.load_token() is None  # 손상 시 조용히 None


# --- handoff 콜백 본문 파싱 -----------------------------------------------------

def test_parse_body_form():
    raw = b"state=xyz&access=mym_123"
    out = _parse_body("application/x-www-form-urlencoded", raw)
    assert out == {"state": "xyz", "access": "mym_123"}


def test_parse_body_json():
    out = _parse_body("application/json", b'{"state":"xyz","access":"mym_123"}')
    assert out == {"state": "xyz", "access": "mym_123"}


def test_parse_body_bad_json():
    assert _parse_body("application/json", b"{oops") == {}


# --- client: 요청마다 최신 토큰 주입 -------------------------------------------

def test_mymauth_injects_bearer(monkeypatch):
    monkeypatch.setattr(tokens, "load_token", lambda: "mym_live")
    auth = client.MymAuth()
    req = httpx.Request("POST", "http://localhost:4000/api/mcp")
    flow = auth.auth_flow(req)
    sent = next(flow)
    assert sent.headers["Authorization"] == "Bearer mym_live"


def test_mymauth_no_token_no_header(monkeypatch):
    monkeypatch.setattr(tokens, "load_token", lambda: None)
    auth = client.MymAuth()
    req = httpx.Request("POST", "http://localhost:4000/api/mcp")
    sent = next(auth.auth_flow(req))
    assert "Authorization" not in sent.headers


def test_current_base_url_ignores_env(monkeypatch):
    # env 는 더 이상 대상 결정에 관여하지 않는다 — active 부재 시 dev 기본으로 폴백
    monkeypatch.setattr(tokens, "get_active", lambda: None)
    monkeypatch.setenv("MYMY_BASE_URL", "https://mymy.example.com/")
    assert client.current_base_url() == "http://localhost:4000"


def test_current_base_url_active_wins_over_env(monkeypatch):
    # active 인스턴스가 대상 — env 를 세팅해도 무시된다
    monkeypatch.setattr(tokens, "get_active", lambda: "http://koba-mymy.gemiso.com")
    monkeypatch.setenv("MYMY_BASE_URL", "https://mymy.example.com")
    assert client.current_base_url() == "http://koba-mymy.gemiso.com"


def test_current_base_url_dev_default(monkeypatch):
    monkeypatch.setattr(tokens, "get_active", lambda: None)
    monkeypatch.delenv("MYMY_BASE_URL", raising=False)
    assert client.current_base_url() == "http://localhost:4000"


def test_transport_url_follows_active(tmp_path, monkeypatch):
    # 동적 프록시의 척추: make_transport() 는 매 호출 active 인스턴스로 URL 을 만든다.
    # active 를 바꾸면 다음 transport 가 그 서버를 향한다(프로세스 재시작 없이 전환).
    cred = tmp_path / "credentials.json"
    monkeypatch.setattr(tokens, "_cred_path", lambda: cred)
    monkeypatch.delenv("MYMY_BASE_URL", raising=False)

    tokens.save_instance("http://localhost:4000", "mym_l", "http://localhost:3000", "local")
    assert client.make_transport().url == "http://localhost:4000/api/mcp"

    tokens.set_active("http://koba-mymy.gemiso.com")
    assert client.make_transport().url == "http://koba-mymy.gemiso.com/api/mcp"
