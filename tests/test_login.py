"""mymy_login 오케스트레이션 단위 테스트.

케이스 분류: Happy(선택지·전환) / Validation(target 해석·프로브) / External(핸드오프 미호출).
tokens 경로는 tmp 로 격리, browser_handoff·probe_mymy 는 monkeypatch 로 대체(네트워크·브라우저 없음).
"""

from __future__ import annotations

import pytest

from mymy_mcp import login as login_mod
from mymy_mcp import tokens


@pytest.fixture
def isolate(tmp_path, monkeypatch):
    cred = tmp_path / "credentials.json"
    monkeypatch.setattr(tokens, "_cred_path", lambda: cred)
    # 기본: 핸드오프/프로브가 실제로 호출되면 테스트 실패로 드러나게 스파이 설치
    calls = {"handoff": [], "probe": []}

    def fake_handoff(web_url):
        calls["handoff"].append(web_url)
        return {"access": "mym_new"}

    def fake_probe(base):
        calls["probe"].append(base)
        return True

    monkeypatch.setattr(login_mod, "browser_handoff", fake_handoff)
    monkeypatch.setattr(login_mod, "probe_mymy", fake_probe)
    return calls


# --- 선택 UX: 무인자 → choices --------------------------------------------------

def test_no_arg_returns_choices(isolate):
    out = login_mod.login()
    assert out["needs_selection"] is True
    assert isolate["handoff"] == []  # 브라우저 안 엶
    names = {c["name"] for c in out["choices"]}
    assert {"local", "koba"} <= names


def test_choices_reflect_active_and_authenticated(isolate):
    tokens.save_instance("http://localhost:4000", "mym_l", "http://localhost:3000", "local")
    out = login_mod.login()
    assert out["active"] == "http://localhost:4000"
    by_name = {c["name"]: c for c in out["choices"]}
    assert by_name["local"]["authenticated"] is True
    assert by_name["koba"]["authenticated"] is False


def test_choices_include_remembered_non_preset(isolate):
    tokens.save_instance("http://custom:4000", "mym_c", "http://custom:4000", "custom")
    out = login_mod.login()
    bases = {c["base_url"] for c in out["choices"]}
    assert "http://custom:4000" in bases


# --- 전환: 인증된 인스턴스는 브라우저 없이 active 만 ---------------------------

def test_switch_cached_no_handoff(isolate):
    tokens.save_instance("http://localhost:4000", "mym_l", "http://localhost:3000", "local")
    tokens.set_active("http://koba-mymy.gemiso.com")  # active 를 다른 곳으로

    out = login_mod.login("local")
    assert out == {"switched": True, "base_url": "http://localhost:4000", "cached": True}
    assert isolate["handoff"] == []  # 재로그인 없음
    assert tokens.get_active() == "http://localhost:4000"


def test_switch_by_base_url(isolate):
    tokens.save_instance("http://localhost:4000", "mym_l", "http://localhost:3000", "local")
    tokens.set_active("http://koba-mymy.gemiso.com")
    out = login_mod.login("http://localhost:4000")
    assert out["switched"] is True
    assert isolate["handoff"] == []


def test_force_reauth_opens_handoff(isolate):
    tokens.save_instance("http://localhost:4000", "mym_l", "http://localhost:3000", "local")
    out = login_mod.login("local", force=True)
    assert out["logged_in"] is True
    assert isolate["handoff"] == ["http://localhost:3000"]  # 프리셋 web_url 로 핸드오프
    assert isolate["probe"] == []  # 프리셋은 프로브 생략


# --- 프리셋 신규 로그인(토큰 없음): 프로브 생략, 핸드오프 --------------------

def test_preset_new_login_skips_probe(isolate):
    out = login_mod.login("koba")
    assert out["logged_in"] is True
    assert out["base_url"] == "http://koba-mymy.gemiso.com"
    assert isolate["handoff"] == ["http://koba-mymy.gemiso.com"]
    assert isolate["probe"] == []  # 프리셋 신뢰 → 프로브 생략
    # 저장 + active
    assert tokens.token_for("http://koba-mymy.gemiso.com") == "mym_new"
    assert tokens.get_active() == "http://koba-mymy.gemiso.com"


# --- 임의 URL: 프로브 통과 → 핸드오프 / 실패 → 거부 --------------------------

def test_arbitrary_url_probe_pass_then_handoff(isolate):
    out = login_mod.login("http://new-mymy:4000")
    assert out["logged_in"] is True
    assert isolate["probe"] == ["http://new-mymy:4000"]
    assert isolate["handoff"] == ["http://new-mymy:4000"]  # base == web
    assert tokens.token_for("http://new-mymy:4000") == "mym_new"


def test_arbitrary_url_probe_reject_no_handoff(isolate, monkeypatch):
    monkeypatch.setattr(login_mod, "probe_mymy", lambda base: False)
    out = login_mod.login("http://evil:4000")
    assert out["error"] == "not_mymy"
    assert isolate["handoff"] == []  # 브라우저 미실행


def test_invalid_scheme_rejected(isolate):
    out = login_mod.login("ftp://x")
    assert out["error"] == "invalid_url"
    assert isolate["handoff"] == []
    assert isolate["probe"] == []


def test_non_url_rejected(isolate):
    out = login_mod.login("just-a-string")
    assert out["error"] == "invalid_url"
    assert isolate["handoff"] == []


# --- 기억된 임의 인스턴스는 이후 프로브 생략 -----------------------------------

def test_remembered_arbitrary_switch_skips_probe(isolate):
    # 최초 로그인(프로브 1회)
    login_mod.login("http://new-mymy:4000")
    isolate["probe"].clear()
    isolate["handoff"].clear()
    tokens.set_active("http://localhost:4000")  # active 이동

    # 재선택 → 기억된 인스턴스라 cached 전환(프로브·핸드오프 없음)
    out = login_mod.login("http://new-mymy:4000")
    assert out["switched"] is True
    assert isolate["probe"] == []
    assert isolate["handoff"] == []
