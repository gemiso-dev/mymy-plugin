# mymy-mcp-plugin

Claude Code / Claude Desktop 에서 **MYMY MCP 도구**(검색·콘텐츠 조회 등)를 쓰기 위한 플러그인.
관리 UI에서 `mym_` 토큰을 수기로 복사하는 대신, **`/mymy-login` 한 번**이면 브라우저가 열리고
(이미 MYMY 웹에 로그인돼 있으면) "연결 허용"만 눌러 자동 인증된다. 토큰은 로컬에 저장되어
이후 창을 열면 이미 인증된 상태다(만료 90일 / 철회 시에만 재로그인).

> 공개 레포 `gemiso-dev/mymy-plugin` (Python/uv, 자체 완결 구조). 이 레포 자체가 Claude Code
> **플러그인 마켓플레이스** 역할을 한다 — 별도 클론 없이 Claude Code 안에서 바로 설치한다.

---

## 요구 사항

| 항목 | 설명 |
|------|------|
| **[uv](https://docs.astral.sh/uv/)** | Python 3.13+ 런타임 (플러그인 서버 실행) |
| **Google Chrome** | 브라우저 핸드오프 인증 창 |
| **MYMY 계정** | `mcp.access` 그룹 권한 (관리자에게 요청) |

---

## 설치 (Claude Code)

Claude Code 안에서 아래 두 줄만 실행하면 된다. **레포를 클론할 필요 없다.**

```bash
/plugin marketplace add gemiso-dev/mymy-plugin
/plugin install mymy-mcp-plugin@mymy-marketplace
```

- 1줄: 이 레포를 마켓플레이스로 등록
- 2줄: `<플러그인명>@<마켓플레이스명>` 형식으로 설치 (이름은 각각 `mymy-mcp-plugin`,
  `mymy-marketplace` 로 고정 — 레포의 `.claude-plugin/*.json` 에서 옴)

설치하면 플러그인의 MCP 서버(`.mcp.json`)가 **자동 등록**된다. 현재 세션에 바로 반영하려면:

```bash
/reload-plugins        # 또는 Claude Code 재시작
```

### 첫 로그인

```bash
/mymy-login            # 인자 없이 실행하면 접속할 인스턴스 선택지가 뜬다
/mymy-login local      # 또는 프리셋/URL 을 바로 지정
```

브라우저가 열리면 MYMY 웹 로그인(이미 로그인 상태면 생략) 후 "연결 허용"을 누른다. 끝.

---

## 업데이트

```bash
/plugin marketplace update mymy-marketplace          # 레포 최신 내용 fetch
/plugin update mymy-mcp-plugin@mymy-marketplace      # 플러그인을 새 버전으로 갱신
/reload-plugins                                      # 또는 Claude Code 재시작
```

> `/plugin` → **Marketplaces** 탭에서 auto-update 를 켜두면 `marketplace update` 를 수동으로
> 돌리지 않아도 백그라운드로 최신화된다. 그래도 세션 반영엔 `/reload-plugins`(또는 재시작)가 필요.

---

## 사용 — 여러 MYMY 서버 오가기

**연결 대상은 `/mymy-login` 으로만 정한다 (별도 env 설정 없음).** 최초부터 프리셋/URL 을 골라
연결하며, 로그인 전 fallback 은 코드 기본(localhost dev)이다.

- `mymy_login("local")` / `mymy_login("docker")` / `mymy_login("koba")` / `mymy_login("https://<도메인>")`
- 인자 없이 호출하면 선택지(프리셋 ∪ 이미 로그인한 인스턴스)를 받아 고른다.
- 이미 로그인한 인스턴스로는 재로그인 없이 즉시 전환된다(active 포인터만 이동).

프리셋에 없는 커스텀 서버는 최초 1회 URL 을 직접 넣어 로그인하면 이후 기억되어 선택지에 뜬다.

---

## 동작 방식

1. `/mymy-login` → 로컬 `127.0.0.1` loopback 서버 기동 + Chrome 으로 `<web>/mcp-auth` 오픈.
2. MYMY 웹이 로그인 세션(localStorage JWT)으로 `mym_` 토큰을 자동 발급받아 loopback 으로 전달.
3. 토큰은 `~/.mymy-mcp/credentials.json` 에 인스턴스별로 저장.
4. 이후 모든 도구 호출은 이 토큰으로 MYMY `/api/mcp` 에 **투명 프록시**된다 — 도구를 재정의하지
   않으므로 서버에 도구가 추가돼도 플러그인은 그대로다.

---

## 제거 / 비활성화

```bash
/plugin disable mymy-mcp-plugin@mymy-marketplace     # 잠시 끄기(설치는 유지)
/plugin enable  mymy-mcp-plugin@mymy-marketplace     # 다시 켜기
/plugin uninstall mymy-mcp-plugin@mymy-marketplace   # 완전 제거
```

---

## Claude Desktop (플러그인 마켓플레이스 미지원, 대안)

Claude Desktop 은 플러그인 마켓플레이스를 지원하지 않으므로, 공개 레포에서 **클론 없이** uvx 로
직접 실행하도록 등록한다. `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mymy": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/gemiso-dev/mymy-plugin.git", "mymy-mcp"]
    }
  }
}
```

앱 재시작 후 "+" 메뉴의 `mymy_login` 프롬프트로 인증한다. 최신 버전 반영은 앱 재시작으로 이뤄지며,
캐시가 갱신되지 않으면 `args` 에 `"--refresh"` 를 추가한다.

---

## 개발

```bash
uv sync
uv run pytest                              # 단위 테스트
uv run python -m mymy_mcp.server login     # CLI 로 핸드오프만 수동 실행
```

---

## 보안

- loopback 콜백은 `127.0.0.1` 바인딩 + Host 헤더 검증(DNS rebinding 방어), 1회용 `state`.
- 토큰은 로컬 파일에만 저장(커밋·로그 금지). 철회는 MYMY 관리 UI의 API 키 목록에서.
