"""신규 URL 안전장치 — MYMY 대상 프로브 (안전장치 a).

프리셋/기억에 없는 임의 URL 을 처음 연결할 때, 브라우저 핸드오프를 열기 **전에**
`GET <target>/llms.txt` 로 그 URL 이 실제 MYMY 서버인지 검증한다. 200 이면서 본문이
llms.txt 구조 마커를 포함할 때만 통과한다.

마커는 **대소문자·브랜드 표기에 의존하지 않는 구조 문자열**을 쓴다:
  필수: `/api/mcp` 선언 라인 존재 AND (`Model Context Protocol` OR `## MCP tools`) 존재.

⚠️ 리터럴 대문자 `"MYMY"` 로 검사하지 말 것 — 실제 llms.txt 본문은 "MyMy"(혼합 대소문자)를
쓰므로 대문자 매칭 시 모든 실서버가 false-negative 가 되어 신규 로그인이 영구 불가해진다.
아래는 브랜드 문자열을 아예 검사하지 않아 이 함정을 구조적으로 회피한다.
"""

from __future__ import annotations

import httpx

_TIMEOUT = 5.0


def has_mymy_markers(body: str) -> bool:
    """llms.txt 본문이 MYMY 구조 마커를 포함하는지(대소문자 무시)."""
    if "/api/mcp" not in body:
        return False
    low = body.lower()
    return ("model context protocol" in low) or ("## mcp tools" in low)


def fetch_llms_txt(base_url: str, timeout: float = _TIMEOUT) -> tuple[int, str] | None:
    """`GET <base>/llms.txt` → (status, body). 네트워크 실패 시 None.

    (테스트는 이 함수만 monkeypatch 하면 프로브 로직을 네트워크 없이 검증할 수 있다.)
    """
    url = f"{base_url.rstrip('/')}/llms.txt"
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
    except httpx.HTTPError:
        return None
    return resp.status_code, resp.text


def probe_mymy(base_url: str) -> bool:
    """base_url 이 실제 MYMY 서버인지 검증(200 + 구조 마커). 아니면 False."""
    got = fetch_llms_txt(base_url)
    if got is None:
        return False
    status, body = got
    return status == 200 and has_mymy_markers(body)
