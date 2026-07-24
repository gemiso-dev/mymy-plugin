# MCP 도구 레퍼런스

이 플러그인이 MYMY 서버 `/api/mcp` 에서 **투명 프록시**하는 도구들의 상세 레퍼런스다.
설치·로그인·업데이트는 [README.md](README.md) 를 참조한다 — 이 문서는 **도구 사용법**만 다룬다.

- 각 도구는 **서버측 권한을 그대로 적용** — 토큰 사용자가 일반 `/api/*` 화면에서 볼 수 있는
  데이터만 노출된다.
- 모든 도구 호출은 서버 감사 로그에 기록된다 (누가 / 어떤 도구 / 인자 요약 — `submit_feedback`
  본문은 제외).
- 모든 도구의 description·필드 라벨은 영어로 작성되며, 결과는 스키마로 고정된 필드만 반환된다.

## 제공 도구

| 도구 | 용도 | 권한 게이트 |
|------|------|------------|
| `search_contents` | AND/OR(BM25 전문 검색) 또는 AI(시맨틱/벡터) 모드 검색 — `search_mode` 파라미터로 선택 | 카테고리 권한 범위 내 결과만; AI 모드는 인스턴스 벡터 검색 설정에 따라 사용 불가 가능 |
| `search_in_content` | 단일 콘텐츠 내 위치(페이지/타임코드) 검색 | 콘텐츠 READ 권한, 미존재 404 |
| `list_contents` | 카테고리/정렬 기준 콘텐츠 목록(브라우즈) | 접근 가능 카테고리만 |
| `get_content` | 콘텐츠 단건 상세 메타데이터 + 모든 파일 접근 URL | 콘텐츠 READ 권한, 미존재 404; STT 자막은 `stt.view_result` 그룹 권한 + STT 라이센스 추가 필요 |
| `submit_feedback` | 개선/버그 요청 수집 | `mcp.access` 만 |
| `get_content_persons` | 콘텐츠에 인식된 인물 목록 조회 (페이지네이션, 경량) | 콘텐츠 READ 권한 + `persons` 그룹 권한 + Persona 라이센스(`USE_PERSONA`) |
| `get_person` | 인물 UUID로 전체 전기 정보 단건 조회 (on-demand) | `persons` 그룹 권한 + Persona 라이센스(`USE_PERSONA`) |
| `list_categories` | 카테고리 트리 조회 또는 이름/경로 키워드로 categoryId 탐색 | 카테고리 권한 게이트 ON 환경에서 접근 가능 카테고리만 반환; SYSTEM_ADMIN 우회 |
| `update_content` | 콘텐츠 메타데이터 필드 수정 (PATCH 방식 — 지정한 필드만 갱신). `fields` 맵의 키는 유니크 `fieldCode`(title/description/tags 등). ext 확장 메타 포함. | 콘텐츠 WRITE 권한 필수 |
| `get_metadata_schema` | 활성 메타필드 정의 목록 조회 (fieldCode/dataType/required/valueListCode 등). lang 파라미터로 ko/en/es 라벨 선택. | `mcp.access` 만 |
| `list_code_values` | 코드성 메타필드의 유효 코드값 목록 조회. get_metadata_schema 에서 valueListCode 있는 필드의 `fieldCode` 로 호출. | `mcp.access` 만 |
| `get_content_analysis_prompt` | UMSL v1.2 콘텐츠 분석 재료 반환(타입별 분기): VIDEO → CS-SSL v2.3 프롬프트·콘택트시트 URL·스프라이트 스펙·자막 URL(장시간 영상은 사전 분할된 콘택트시트 청크 `chunks[]` 추가 제공); AUDIO → AS-SEL v2.0 프롬프트·STT(SRT) 기반. 비전/STT 추론은 클라이언트가 수행. | 콘텐츠 READ 권한 + (VIDEO: GRID 파일 / AUDIO: STT 자막) 필요 |
| `attach_content_analysis` | UMSL v1.2 분석 JSON 결과(asset + segments[])를 `segment_info` 파일 메타필드에 저장(재호출 시 교체). | 콘텐츠 WRITE 권한 |

## search_contents 상세

### 입력 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `query` | string (2-200자) | (필수) | 검색 키워드 |
| `search_mode` | `and` \| `or` \| `ai` | `and` | 검색 모드 (아래 설명 참조) |
| `limit` | integer 1-50 | 20 | 페이지당 결과 수 |
| `page` | integer ≥ 1 | 1 | 페이지 번호 (and/or 모드만 적용; ai는 단일 페이지) |
| `contentTypes` | string[] | - | 콘텐츠 유형 필터 (video, image, document, audio) |
| `categoryIds` | string[] | - | 카테고리 ID 필터 (사용자 권한 범위 내) |
| `searchScope` | `metadata` \| `full` \| `chunks_only` | 시스템 설정 | 검색 범위 (and/or 모드만 적용) |

### search_mode 설명

| 모드 | 방식 | 사용 가능 여부 |
|------|------|----------------|
| `and` | BM25 전문 검색 — 모든 단어 포함 | **항상 사용 가능** |
| `or` | BM25 전문 검색 — 임의 단어 포함 | **항상 사용 가능** |
| `ai` | 자연어 시맨틱/벡터 검색 | **인스턴스 설정에 따라 조건부** |

AI 모드(`search_mode=ai`)는 다음 조건이 모두 충족되어야 사용 가능하다:
1. 시스템 설정 `vectorSearch.enabled` 활성화
2. 임베딩 어댑터(API 키) 설정 완료

미충족 시 도구는 사유별 에러를 반환하며, `search_mode=and` 또는 `search_mode=or` 로 재시도하도록 안내한다. AI 모드는 `vectorScope=metadata`(라이센스 불필요)로 고정되어 동작한다.

### 출력

```json
{
  "searchMode": "and",
  "items": [
    {
      "contentId": "...",
      "contentType": "VIDEO",
      "title": "제목",
      "createdAt": "2026-01-01T00:00:00.000Z",
      "match": "metadata",
      "score": 12.5,
      "thumbnailUrl": "..."
    }
  ],
  "pagination": { "page": 1, "pageSize": 20, "totalCount": 5, "totalPages": 1 }
}
```

AI 모드 결과는 `match: "semantic"`, `score: 0`, `similarity: 0.87`(코사인 유사도 0-1) 형태로 반환되며 `pagination`은 단일 페이지로 고정된다.

## list_categories — 카테고리 탐색 도구

카테고리 ID를 모르는 상태에서 카테고리를 탐색하거나 이름/경로로 `categoryId`를 찾을 때 사용한다. `list_contents`나 `search_contents`에서 `categoryId`가 필요할 때 먼저 호출한다.

### 동작 모드

- **목록 모드** (`query` 생략): 활성 카테고리 전체 트리를 깊이 우선 순서의 평면 배열로 반환.
  - `parentId` 지정 시 해당 노드의 하위 카테고리만 반환 (기본: 전체 하위 트리, `recursive=false`이면 직속 자식만).
- **검색 모드** (`query` 지정): 이름 또는 경로 키워드(ILIKE)로 카테고리 검색 → `categoryId` 조회에 활용.

### 입력 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `query` | string | - | 검색 키워드 (이름 또는 경로). 지정하면 검색 모드 |
| `parentId` | string | - | 목록 모드: 이 카테고리의 하위 노드만 반환 |
| `recursive` | boolean | true | 목록 모드: `true`이면 전체 하위 트리, `false`이면 직속 자식만 |
| `limit` | integer 1-100 | 50 | 반환할 최대 항목 수 |

### 출력

```json
{
  "items": [
    {
      "categoryId": "42",
      "name": "스포츠",
      "parentId": "10",
      "depth": 1,
      "path": "/kbs/kbs-sports",
      "namePath": "KBS/스포츠"
    }
  ]
}
```

- `path`: 코드 기반 구체화 경로 (DB `path` 컬럼 원본).
- `namePath`: 이름 기반 경로 — 표시 또는 다른 도구 호출 시 식별용으로 활용 권장.

### 사용 예

```json
// categoryId를 모를 때 이름으로 검색
{ "query": "스포츠", "limit": 10 }

// 루트 카테고리만 조회
{ "recursive": false }

// 특정 카테고리의 직속 자식 조회
{ "parentId": "10", "recursive": false }
```

## 인물 조회 도구 (get_content_persons / get_person)

인물 정보는 2단계 도구로 제공된다. `get_content_persons` 로 콘텐츠 내 인물 목록(경량)을 페이지 단위로 조회한 뒤, 관심 인물의 `personId` 로 `get_person` 을 호출해 상세 바이오 정보를 가져온다.

### get_content_persons 입력

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `contentId` | string | (필수) | 콘텐츠 ID (`search_contents` / `list_contents` / `get_content` 에서 획득) |
| `page` | integer ≥ 1 | 1 | 페이지 번호 |
| `limit` | integer 1-100 | 20 | 페이지당 결과 수 |
| `sort` | `faceCount` \| `similarity` \| `name` | `faceCount` | 정렬: 등장 빈도 내림차순 / 유사도 내림차순 / 이름 오름차순 |

### get_content_persons 출력

```json
{
  "contentId": "...",
  "persons": [
    {
      "personId": "uuid",
      "name": "홍길동",
      "englishName": "Hong Gildong",
      "faceCount": 5,
      "bestSimilarity": 0.94,
      "verified": true
    }
  ],
  "pagination": { "page": 1, "limit": 20, "total": 3, "totalPages": 1 }
}
```

### get_person 입력

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `personId` | string | 인물 UUID (`get_content_persons` 에서 획득) |

### get_person 출력

```json
{
  "personId": "uuid",
  "name": "홍길동",
  "englishName": "Hong Gildong",
  "role": "대표이사",
  "gender": "male",
  "nationality": "KR",
  "birthDate": "1980-01-15",
  "faceCount": 42,
  "verified": true,
  "representativeFaceId": "uuid-or-null"
}
```

> **참고**: `organization`(소속) 및 `tags` 필드는 현재 스키마에 존재하지 않아 제공되지 않는다.

## get_content 응답 files 블록

`get_content` 는 `files` 블록을 통해 모든 파일 접근 URL을 반환한다. 각 URL은 단기 토큰이 포함된 nginx-files 직접 URL이다.

| 필드 | 권한 게이트 | 미충족 시 |
|------|------------|----------|
| `files.original` | 콘텐츠 READ | 원본 행 없음/삭제 시 `null` |
| `files.original.downloadUrl` | MANAGED + nginx 설정 | SMI 또는 nginx 미설정 시 `null` |
| `files.proxyUrl` / `thumbnailUrl` / `catalogGridUrl` / `catalogVttUrl` | 콘텐츠 READ | `null` |
| `files.subtitles` | 콘텐츠 READ + `stt.view_result` 그룹 권한 + STT 라이센스 | `null` (권한/라이센스 없음), `[]` (nginx 미설정) |

SMI 원본: `downloadable=false`, `downloadUrl=null`, `path=displayPath` (클립보드 복사용 외부 경로).

## 콘텐츠 분석 도구 (UMSL v1.2)

콘텐츠를 분석하여 결과를 **통합 미디어 세그먼트 로그(UMSL v1.2, `asset / segments[] / units[]`)** 로 `segment_info` 파일 메타필드에 저장하는 2종 도구다. 콘텐츠 타입별로 분석 프롬프트가 분기된다:

- **VIDEO** → CS-SSL v2.3 (Contact-Sheet Scene & Shot Logging) — 콘택트시트(스프라이트) + 자막 기반
- **AUDIO** → AS-SEL v2.0 (Audio-Speech Segment & Element Logging) — STT(SRT) 기반

두 프롬프트 모두 출력 구조는 UMSL v1.2 로 통일되며, `asset.modality`(`video`/`audio`)와 segment/unit 의 `track` 으로 판별한다.

### 흐름

```
1. get_content_analysis_prompt(contentId)
   → (타입별) 시스템 프롬프트 + 분석 재료 반환
     VIDEO: 콘택트시트 URL + 스프라이트 스펙 + 자막 URL
     AUDIO: STT(SRT) 자막 기반 (콘택트시트 없음, 스펙트로그램은 후속)

2. 클라이언트 비전/STT 추론
   → VIDEO: contactSheet.url 이미지를 비전 모델에 첨부 + prompt + spriteSpec + subtitle + granularity
   → AUDIO: STT(SRT) 자막을 기반으로 prompt + granularity
   → UMSL v1.2 JSON 생성

3. attach_content_analysis(contentId, result)
   → 분석 결과 UMSL JSON을 segment_info 파일 메타필드에 저장
   → 재호출 시 기존 파일 교체(결정적 파일명)
```

### get_content_analysis_prompt

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `contentId` | string | (필수) | 대상 콘텐츠 ID (VIDEO 또는 AUDIO) |
| `granularity` | `both` \| `segment` | `both` | 분석 세분도. `both`=Segment+Unit, `segment`=Segment만 |

제약: VIDEO 타입은 GRID(카탈로그) 파일, AUDIO 타입은 STT(SRT) 자막 + STT 조회 권한 필수. 미충족 시 에러 반환.

### attach_content_analysis

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `contentId` | string | 대상 콘텐츠 ID |
| `result` | object \| string | UMSL v1.2 분석 결과 JSON. 객체 또는 JSON 문자열 허용. 최상위 `asset` 객체 + `segments` 배열 필요 |

저장된 파일은 콘텐츠 상세 패널 "파일" 섹션에서 다운로드 가능하다.

## 피드백 처리

`submit_feedback` 으로 제출된 본문은 운영 측 전용 로그에 분리 기록되며, 도구 호출 사실(누가/언제)과는 별도로 보관된다. 기본 보관 기간은 30일이다.
