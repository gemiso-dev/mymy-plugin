# mymy-mcp-plugin

Claude Code / Claude Desktop 에서 **MYMY MCP 도구**(검색·콘텐츠 조회 등)를 쓰기 위한 플러그인.
관리 UI에서 `mym_` 토큰을 수기로 복사하는 대신, **`/mymy-login` 한 번**이면 브라우저가 열리고
(이미 MYMY 웹에 로그인돼 있으면) "연결 허용"만 눌러 자동 인증된다. 토큰은 로컬에 저장되어
이후 창을 열면 이미 인증된 상태다(만료 90일 / 철회 시에만 재로그인).

> 공개 레포 `gemiso-dev/mymy-plugin` (Python/uv, 자체 완결 구조). 이 레포 자체가 Claude Code
> **플러그인 마켓플레이스** 역할을 한다 — 별도 클론 없이 Claude Code 안에서 바로 설치한다.

---

## 요구 사항

클론·빌드용이 아니라 **실행·인증에 필요한 항목**이다(마켓플레이스로 설치해도 동일).

| 항목 | 설명 |
|------|------|
| **[uv](https://docs.astral.sh/uv/)** | Python 3.13+ 런타임. Claude Code 가 플러그인 서버를 `uv run` 으로 실행하므로 필수 |
| **Google Chrome** | 핸드오프 인증 창 (권장 — 없으면 기본 브라우저로 폴백) |
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

기본 프리셋:

| 프리셋 | API (base_url) | Web (web_url) | 용도 |
|--------|----------------|----------------|------|
| `local` | `http://localhost:4000` | `http://localhost:3000` | 로컬 dev (API·web 분리 실행) |
| `docker` | `http://localhost:8088` | `http://localhost:8088` | 도커 통합 스택 (API·web 동일 오리진) |
| `koba` | `http://koba-mymy.gemiso.com` | `http://koba-mymy.gemiso.com` | 운영 단일 도메인 (http) |

프리셋에 없는 커스텀 서버는 최초 1회 URL 을 직접 넣어 로그인하면 이후 기억되어 선택지에 뜬다.

---

## 제공 도구

플러그인은 도구를 재구현하지 않고 MYMY 서버의 `/api/mcp` 도구를 **투명 프록시**한다. 따라서
아래 목록은 서버가 노출하는 도구이며, 서버에 도구가 추가되면 플러그인 수정 없이 그대로 늘어난다.
각 도구는 **서버측 권한을 그대로 적용** — 토큰 사용자가 일반 화면에서 볼 수 있는 데이터만 나온다.

| 도구 | 용도 |
|------|------|
| `search_contents` | AND/OR(BM25 전문 검색) 또는 AI(시맨틱/벡터) 모드로 콘텐츠 검색 |
| `search_in_content` | 단일 콘텐츠 내 일치 위치(페이지/타임코드) 탐색 |
| `list_contents` | 카테고리·정렬 기준 콘텐츠 목록 브라우즈 |
| `list_categories` | 카테고리 트리 조회 / 이름·경로로 `categoryId` 찾기 |
| `get_content` | 콘텐츠 단건 상세 메타데이터 + 파일 접근 URL |
| `get_metadata_schema` | 활성 메타데이터 필드 정의(타입·필수·코드리스트 참조) 목록 |
| `list_code_values` | 코드형 메타 필드(`fieldCode`)의 유효 코드값 조회 |
| `update_content` | `fieldCode` 단위 메타데이터 수정 (PATCH — 지정 필드만, 카테고리 WRITE 권한) |
| `get_content_persons` | 콘텐츠에 인식된 인물 목록 (경량, 페이지네이션) |
| `get_person` | `personId` 로 인물 상세 바이오 조회 |
| `get_content_analysis_prompt` | UMSL v1.2 분석 재료 준비 (VIDEO → CS-SSL / AUDIO → AS-SEL 분기) |
| `attach_content_analysis` | UMSL v1.2 분석 결과(JSON)를 콘텐츠 `segment_info` 에 첨부 |
| `submit_feedback` | 개선/버그 요청 제출 (서버측 로그 기록) |

> 인증 도구 `mymy_login` (= `/mymy-login` 슬래시)은 프록시 대상이 아니라 이 플러그인이 제공하는
> 로그인/전환용 도구다. 모든 도구 호출은 서버 감사 로그에 기록된다(`submit_feedback` 본문 제외).

각 도구의 입력 파라미터·출력 스키마·권한 게이트 상세는 [MCP.md](MCP.md) 참조.

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

Claude Desktop 은 플러그인 마켓플레이스를 지원하지 않으므로 MCP 서버를 직접 등록한다.

### 1단계 — 한 번만 설치

git 이 정상 동작하는 일반 터미널/PowerShell 에서 실행한다(clone/build 를 미리 끝내둔다):

```powershell
uv tool install --from git+https://github.com/gemiso-dev/mymy-plugin.git mymy-mcp
```

`mymy-mcp` 실행파일이 uv 도구 경로(`~/.local/bin`)에 설치되고, uv 가 이 폴더를 PATH 에 등록한다.

### 2단계 — Claude Desktop 설정 열기

1. Claude Desktop 실행 → 좌측 상단 메뉴(또는 앱 설정)에서 **Settings(설정)** 열기.
2. **Developer(개발자)** 탭 선택 → **Edit Config(설정 편집)** 버튼 클릭.
3. `claude_desktop_config.json` 이 있는 폴더가 탐색기로 열린다. 그 파일을 메모장 등으로 연다.
   - 직접 찾아갈 경우 경로: `%APPDATA%\Claude\claude_desktop_config.json`
     (탐색기 주소창에 `%APPDATA%\Claude` 붙여넣으면 바로 이동. 파일이 없으면 새로 만든다.)

### 3단계 — 설정 붙여넣기

파일이 비어 있으면(또는 새로 만들었으면) 아래를 **그대로 복붙**한다:

```json
{
  "mcpServers": {
    "mymy": {
      "command": "mymy-mcp"
    }
  }
}
```

이미 다른 MCP 서버가 등록돼 있으면 `mcpServers` 안에 `"mymy": { ... }` 부분만 추가한다
(앞 항목 끝의 콤마 `,` 주의):

```json
{
  "mcpServers": {
    "다른서버": { ... },
    "mymy": {
      "command": "mymy-mcp"
    }
  }
}
```

### 4단계 — 재시작 후 로그인

1. Claude Desktop 을 **완전히 종료**한다 — 창만 닫지 말고 트레이 아이콘(우측 하단) 우클릭 → **Quit(종료)**.
2. 다시 실행하면 `mymy` 서버가 뜬다.
3. 채팅창 **"+" 메뉴 → `mymy_login`** 프롬프트로 인증한다.

- **업데이트**: `uv tool upgrade mymy-mcp` (git 되는 일반 터미널에서 1회).
- 재시작 후에도 `mymy-mcp` 를 못 찾으면(드물게 Desktop 이 `~/.local/bin` 을 PATH 에서 못 볼 때),
  `uv tool install` 출력에 찍힌 `mymy-mcp` 실행파일 전체 경로를 `command` 에 넣는다.

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
