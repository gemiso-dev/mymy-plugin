---
description: MYMY 브라우저 핸드오프 인증/재인증 (대상 인스턴스 선택/전환)
argument-hint: "[프리셋명(local/docker/koba) | URL] (생략 시 선택지 제시)"
---

`mymy_login` 도구를 호출해 MYMY 인증을 실행하세요. 인자로 대상을 넘길 수 있습니다: `$ARGUMENTS`

- **인자가 있으면**: 프리셋명(`local`/`docker`/`koba`) 또는 URL 로 `mymy_login("<값>")` 을 호출하세요.
  - 이미 로그인한 인스턴스면 브라우저 없이 즉시 전환됩니다(`switched: true`).
  - 처음 보는 URL 은 브라우저를 열기 전에 MYMY 서버인지 자동 검증(`/llms.txt` 프로브)합니다.
- **인자가 없으면**: 먼저 인자 없이 `mymy_login()` 을 호출해 **선택지 목록**을 받고,
  사용자에게 "어디로 연결할까요?"를 물은 뒤 고른 값으로 다시 호출하세요.

대상은 프리셋명·base_url·임의 URL 무엇이든 자유롭게 지정할 수 있습니다. 사용자는 보통
자연어로 말하고, 그에 맞춰 `mymy_login` 을 호출하면 됩니다:

```text
"mymy 목록 보여줘"                     → mymy_login()            (선택지만, 브라우저 X)
"mymy 로컬로 로그인"                   → mymy_login("local")
"mymy koba 로 전환"                    → mymy_login("koba")      (재로그인 없이 전환)
"mymy 로그인 https://mymy.acme.com"    → mymy_login("https://mymy.acme.com")  (프로브 후 기억)
mymy_login("http://localhost:4000")    # base_url 로 직접 지정도 가능
mymy_login("koba", force=true)         # 강제 재인증(플래그는 도구 직접 호출)
```

> 연결 대상은 env 가 아니라 이 도구의 인자로만 정해집니다. 프리셋에 없는 커스텀 서버는 최초
> 1회 URL 을 직접 넣어 로그인하면 이후 기억되어 선택지에 뜹니다. (로그인 전 fallback 은 코드
> 기본 localhost dev)

브라우저 창이 열리면 MYMY 웹에 로그인(이미 로그인 상태면 생략) 후 "연결 허용"을 누릅니다.
완료되면 인증 성공 여부와 `base_url` 을 보고하세요.

> 인증은 사용자 PC 단위로 인스턴스별로 `~/.mymy-mcp/credentials.json` 에 저장됩니다.
> 토큰 만료(90일)나 관리자 철회로 도구 호출이 401 이 될 때, 또는 재인증이 필요할 때만
> (`mymy_login("<대상>", force=true)`) 다시 실행하면 됩니다.
