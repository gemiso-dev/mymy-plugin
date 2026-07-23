"""코드 기본 프리셋 — 선택지 출처(1/2). 나머지는 credentials.json 의 기억 인스턴스.

분산 방지를 위해 선택지 출처는 **코드 프리셋 + 기억 인스턴스 2가지만**이며,
`.mcp.json` 의 env 는 선택지에 넣지 않는다(active·기억 부재 시 fallback 전용).
"""

from __future__ import annotations

# koba 는 회사가 참여한 전시회(KOBA show) 명칭이며 고객사명이 아님 → 하드코딩 허용.
# koba 는 http (https 아님). base_url == web_url (운영 단일 도메인).
PRESETS: list[dict] = [
    {"name": "local", "base_url": "http://localhost:4000", "web_url": "http://localhost:3000"},
    {"name": "koba", "base_url": "http://koba-mymy.gemiso.com", "web_url": "http://koba-mymy.gemiso.com"},
]


def preset_by_name(name: str) -> dict | None:
    for p in PRESETS:
        if name == p["name"]:
            return p
    return None


def preset_by_base(base_url: str) -> dict | None:
    norm = base_url.rstrip("/")
    for p in PRESETS:
        if norm == p["base_url"].rstrip("/"):
            return p
    return None
