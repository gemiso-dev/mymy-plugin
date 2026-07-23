"""tokens.py v2 멀티 인스턴스 단위 테스트 (Happy/Boundary).

케이스 분류: Happy(저장/조회/전환) / Boundary(빈 파일·손상·v1 승격).
네트워크 불필요 — credentials.json 경로를 tmp_path 로 격리.
"""

from __future__ import annotations

import json

from mymy_mcp import tokens


def _isolate(tmp_path, monkeypatch):
    cred = tmp_path / "credentials.json"
    monkeypatch.setattr(tokens, "_cred_path", lambda: cred)
    return cred


# --- Boundary: 빈 파일 / 손상 --------------------------------------------------

def test_empty_returns_defaults(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert tokens.get_active() is None
    assert tokens.list_instances() == {}
    assert tokens.load_token() is None
    assert tokens.token_for("http://localhost:4000") is None


def test_corrupt_file_returns_defaults(tmp_path, monkeypatch):
    cred = _isolate(tmp_path, monkeypatch)
    cred.write_text("{ not json", encoding="utf-8")
    assert tokens.get_active() is None
    assert tokens.list_instances() == {}


# --- Happy: 다중 인스턴스 저장/조회/active 전환 --------------------------------

def test_save_multiple_instances_and_switch(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    tokens.save_instance("http://localhost:4000", "mym_local", "http://localhost:3000", "local")
    tokens.save_instance("http://koba-mymy.gemiso.com", "mym_koba", "http://koba-mymy.gemiso.com", "koba")

    # save_instance 는 마지막 저장을 active 로 설정
    assert tokens.get_active() == "http://koba-mymy.gemiso.com"
    assert tokens.load_token() == "mym_koba"

    # 인스턴스별 토큰 조회
    assert tokens.token_for("http://localhost:4000") == "mym_local"
    assert tokens.token_for("http://koba-mymy.gemiso.com") == "mym_koba"
    assert set(tokens.list_instances().keys()) == {
        "http://localhost:4000",
        "http://koba-mymy.gemiso.com",
    }

    # 재로그인 없이 즉시 전환 (active 포인터만 이동)
    tokens.set_active("http://localhost:4000")
    assert tokens.get_active() == "http://localhost:4000"
    assert tokens.load_token() == "mym_local"


def test_load_instance_fields(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    tokens.save_instance("http://localhost:4000/", "mym_x", "http://localhost:3000/", "local")
    inst = tokens.load_instance("http://localhost:4000")  # 정규화 매칭
    assert inst is not None
    assert inst["access"] == "mym_x"
    assert inst["web_url"] == "http://localhost:3000"  # 끝 / 제거
    assert inst["name"] == "local"
    assert isinstance(inst["last_login"], int)


def test_normalize_trailing_slash_same_key(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    tokens.save_instance("http://localhost:4000/", "mym_a", "http://localhost:3000", "local")
    tokens.save_instance("http://localhost:4000", "mym_b", "http://localhost:3000", "local")
    assert list(tokens.list_instances().keys()) == ["http://localhost:4000"]
    assert tokens.token_for("http://localhost:4000") == "mym_b"


# --- Boundary: v1 → v2 무손실 승격 --------------------------------------------

def test_migrate_v1_to_v2(tmp_path, monkeypatch):
    cred = _isolate(tmp_path, monkeypatch)
    monkeypatch.setenv("MYMY_WEB_URL", "http://legacy-web:3000")
    cred.write_text(json.dumps({"access": "mym_old", "base_url": "http://legacy:4000"}), encoding="utf-8")

    # 읽기만 해도 메모리상 승격되어 노출
    assert tokens.get_active() == "http://legacy:4000"
    assert tokens.load_token() == "mym_old"
    inst = tokens.load_instance("http://legacy:4000")
    assert inst["access"] == "mym_old"
    assert inst["web_url"] == "http://legacy-web:3000"  # env fallback

    # 명시적 승격 → 디스크가 v2 구조로 재기록
    assert tokens.migrate_v1_if_needed() is True
    on_disk = json.loads(cred.read_text(encoding="utf-8"))
    assert on_disk["version"] == 2
    assert on_disk["active"] == "http://legacy:4000"
    assert "http://legacy:4000" in on_disk["instances"]
    # 재승격은 no-op
    assert tokens.migrate_v1_if_needed() is False


def test_migrate_v1_web_fallback_to_base(tmp_path, monkeypatch):
    cred = _isolate(tmp_path, monkeypatch)
    monkeypatch.delenv("MYMY_WEB_URL", raising=False)
    cred.write_text(json.dumps({"access": "mym_old", "base_url": "http://legacy:4000"}), encoding="utf-8")
    inst = tokens.load_instance("http://legacy:4000")
    assert inst["web_url"] == "http://legacy:4000"  # env 없으면 base 폴백


# --- 하위호환 표면 -------------------------------------------------------------

def test_backward_compat_save_load_clear(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert tokens.load_token() is None
    tokens.save_token("mym_abc", "http://localhost:4000")
    assert tokens.load_token() == "mym_abc"
    assert tokens.load_base_url() == "http://localhost:4000"
    tokens.clear_token()
    assert tokens.load_token() is None
