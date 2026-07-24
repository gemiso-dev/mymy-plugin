# mymy-mcp-plugin

> **위치**: 독립 레포 `gemiso-dev/mymy-plugin` (Python/uv, 자체 완결 구조). Claude Code 플러그인
> 마켓플레이스로 등록하거나 Claude Desktop 에 stdio MCP 서버로 직접 등록해 사용한다.

Claude Code / Claude Desktop 에서 **MYMY MCP 도구**(검색·콘텐츠 조회 등)를 쓰기 위한 플러그인.
관리 UI에서 `mym_` 토큰을 수기로 복사하는 대신, **`/mymy-login` 한 번**이면 브라우저가 열리고
(이미 MYMY 웹에 로그인돼 있으면) "연결 허용"만 눌러 자동 인증된다. 토큰은 로컬에 저장되어
이후 창을 열면 이미 인증된 상태다(만료 90일 / 철회 시에만 재로그인).

## 동작 방식

1. `/mymy-login` → 로컬 `127.0.0.1` loopback 서버 기동 + Chrome 으로 `<web>/mcp-auth` 오픈.
2. MYMY 웹이 로그인 세션(localStorage JWT)으로 `mym_` 토큰을 자동 발급받아 loopback 으로 전달.
3. 토큰은 `~/.mymy-mcp/credentials.json` 에 저장.
4. 이후 모든 도구 호출은 이 토큰으로 MYMY `/api/mcp` 에 **투명 프록시**된다 — 도구를 재정의하지
   않으므로 서버에 도구가 추가돼도 플러그인은 그대로다.

## 요구 사항

- [uv](https://docs.astral.sh/uv/) (Python 3.13+)
- Google Chrome (핸드오프 브라우저)
- MYMY 계정에 `mcp.access` 그룹 권한

## 설정

**연결 대상은 `/mymy-login` 으로 정한다 — 별도 env 설정이 없다.** 최초부터 프리셋/URL 을
골라 연결하며, 로그인 전 fallback 은 코드 기본(localhost dev)이다.

- `mymy_login("local")` / `mymy_login("docker")` / `mymy_login("koba")` / `mymy_login("https://<도메인>")`
- 인자 없이 호출하면 선택지(프리셋 ∪ 기억 인스턴스)를 받아 고른다.
- 이미 로그인한 인스턴스로는 재로그인 없이 즉시 전환된다(active 포인터만 이동).

### Claude Code

마켓플레이스로 등록 후 설치한다:

```bash
/plugin marketplace add gemiso-dev/mymy-plugin
/plugin install mymy-mcp-plugin@mymy-marketplace
```

설치하면 `.mcp.json` 이 자동 적용된다. 이후 `/mymy-login` 실행.

### Claude Desktop

`claude_desktop_config.json` 에 동일 stdio 서버를 등록:

```json
{
  "mcpServers": {
    "mymy": {
      "command": "uv",
      "args": ["run", "--directory", "<mymy-plugin 클론 절대경로>", "python", "-m", "mymy_mcp.server"]
    }
  }
}
```

앱 재시작 후 "+" 메뉴의 `mymy_login` 프롬프트로 인증한다.

## 개발

```bash
uv sync
uv run pytest          # 단위 테스트
uv run python -m mymy_mcp.server login   # CLI 로 핸드오프만 수동 실행
```

## 보안

- loopback 콜백은 `127.0.0.1` 바인딩 + Host 헤더 검증(DNS rebinding 방어), 1회용 `state`.
- 토큰은 로컬 파일에만 저장(커밋·로그 금지). 철회는 MYMY 관리 UI의 API 키 목록에서.
