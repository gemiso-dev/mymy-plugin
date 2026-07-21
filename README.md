# mymy-mcp-plugin

> **위치**: mymy-v4 레포 내부 `tools/mcp-plugin/` (현재 **내부 전용**). `tools/` 는 npm 워크스페이스
> 밖이라 turbo/`npm ci` 에 영향을 주지 않는다. 외부 배포가 필요해지면 이 폴더를 `git subtree split`
> 으로 별도 공개 레포/마켓플레이스로 분리한다(자체 완결 구조 유지).

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

`.mcp.json` 의 `env` 에서 대상 서버를 지정한다(기본 dev):

```json
"env": { "MYMY_BASE_URL": "https://<배포도메인>", "MYMY_WEB_URL": "https://<배포도메인>" }
```

### Claude Code

플러그인으로 등록하면 `.mcp.json` 이 자동 적용된다. 등록 후 `/mymy-login` 실행.

### Claude Desktop

`claude_desktop_config.json` 에 동일 stdio 서버를 등록:

```json
{
  "mcpServers": {
    "mymy": {
      "command": "uv",
      "args": ["run", "--directory", "<mymy-v4 절대경로>/tools/mcp-plugin", "python", "-m", "mymy_mcp.server"],
      "env": { "MYMY_BASE_URL": "https://<배포도메인>", "MYMY_WEB_URL": "https://<배포도메인>" }
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
