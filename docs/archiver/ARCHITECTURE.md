# Archiver 아키텍처 · 레이어 경계

활성 탭·과거 아카이브·웹 검색을 조합해 답변하는 Archiver LangGraph 에이전트의 타입·모듈 배치·스트리밍·영속성을 정의한다.

---

## 1. 레이어 개요

```
┌─────────────────────────────────────────────────────────────┐
│  extension (사이드패널 채팅 UI)                               │
│    features/chat/useChat.ts · features/archiver/useArchiver │
│    features/archiver/services/archiverClient.ts (REST + SSE)     │
│    features/archiver/services/queryTabContext.ts (TabContext)    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / SSE + Bearer JWT
┌──────────────────────────▼──────────────────────────────────┐
│  app/api/v1/archiver.py       HTTP 라우터 (인증 필수)        │
│       ▼                                                      │
│  app/services/archiver_service.py                            │
│    · 세션/DB I/O · multi-turn messages 조립                  │
│    · ArchiverEngine에 워크플로우 완전 일임                    │
│    · SSE event/data envelope 직렬화                          │
│  app/repositories/archiver_repository.py                     │
│    · 대화 영속 · hybrid RAG (키워드 + pgvector)              │
└──────────────────────────┬──────────────────────────────────┘
                           │ ArchiverStore Port 주입
┌──────────────────────────▼──────────────────────────────────┐
│  app/agents/archiver/         LangGraph 자율 루프 에이전트      │
│    engine.py        ArchiverEngine.stream()                  │
│    workflow.py      StateGraph 정의·compile()                │
│    branches.py      router / evaluator 조건부 fan-out·fan-in │
│    steps/           classify·evaluate·respond·need_dom       │
│    nodes/           collect_node·rag_node·search_node        │
│    core/            constants·store·history·tools              │
│    agents/shared/   gemini.py (Archiver·Curator 공용)        │
│    models/          ArchiverState + RouterTargets·Evaluation·SSE │
│    past_knowledge/  embedding·retrieval (DB hybrid 검색)     │
│    protocols/       SSE envelope·stream_status 메시지 SSOT   │
│    trace/           개발 trace + observability JSON          │
│    utils/           context_body_quality·context_refine 등   │
│    prompts/         프롬프트 템플릿·빌더                      │
└─────────────────────────────────────────────────────────────┘
```

**제어권 분담**

| 레이어 | 담당 |
|--------|------|
| `ArchiverService` | 세션 resolve, user/assistant 로그 저장, 히스토리→`messages` 조립, SSE 전달 |
| `ArchiverEngine` + `workflow.py` | `steps/`(제어)·`nodes/`(수집) 오케스트레이션, evaluator 루프, respond 스트리밍 |
| `ArchiverRepository` | `ai_chat_logs` CRUD, hybrid RAG (`ArchiverStore` 구현) |

---

## 2. LangGraph 워크플로우

```
START
  → router (steps/classify)
       ├─ is_general  → respond → END
       ├─ need_dom    → END (클라이언트 DOM 수집 SSE)
       └─ fan-out     → collect_node | rag_node | search_node (nodes/)
            → evaluator (steps/evaluate)
                 ⇄ (재 fan-out | respond) → respond → END
```

**라우팅 SSOT:** `is_general` + `target_engines` + `context_dom` / `context_rag` / `context_search`. 단일 경로 enum(`ArchiverRoute`)은 제거됨. trace 라벨은 `format_router_trace_label()` (`general` 또는 `collect_node+search_node` 형식).

조건부 분기는 `branches.py`에 두고, `trace/routing.py` + `trace/observability.py`에서 로그를 기록한다.

### 2.1 GENERAL Fast-Path

`is_general` (또는 `target_engines` 비어 있음) → `router → respond → END`. 수집·evaluator·검색 단계를 건너뛴다.

### 2.2 Evaluator 역주행

Gemini 2.5 Flash Structured Output (`Evaluation`)으로 근거 충분성 채점 후:

| 조건 | 다음 노드 |
|------|-----------|
| `is_sufficient` | `respond` |
| `recommended_action=search` & `search_attempts < MAX` | `search` (역주행) |
| `recommended_action=collect` & `retrieval_attempts < MAX` | `collect` (역주행) |
| 한도 초과 | `respond` (best-effort) |

### 2.3 respond

**프롬프트 (`steps/respond_context.py`):** 채워진 `context_*` 기반 `build_synthesis_route_instruction` 하나로 합성. `is_general`이고 수집 근거가 없으면 general 템플릿.

**Tool 바인딩:** Google Search Tool은 **`search_node ∈ target_engines`이면서 `context_search`가 비어 있을 때만** 바인딩한다.

**온도 (`core/constants.py`):** `is_general` → `RESPOND_CHITCHAT_TEMPERATURE` (0.8), 그 외 → `RESPOND_FACTUAL_TEMPERATURE` (0.4).

---

## 3. ArchiverState

`models/state.py` — LangGraph 실행 상태 SSOT. 도메인 타입(`Evaluation`, `RouterTargets` 등)은 `models/` 패키지.

| 필드 | 설명 |
|------|------|
| `messages` | `add_messages` 리듀서 — **multi-turn 히스토리 포함** |
| `user_id` | `uuid.UUID` (`users.id` FK) |
| `session_id` | 대화 세션 (URL 단위 그룹) |
| `is_general` | 일상 대화·인사 fast-path |
| `target_engines` | 1차 병렬 수집 엔진 (`collect_node` / `rag_node` / `search_node`) |
| `route` | *(deprecated, optional)* — 신규 코드에서 쓰지 않음 |
| `context_dom`, `context_rag`, `context_search` | 엔진별 격리 수집 근거 (canonical) |
| `evaluation_result` | evaluator 채점 JSON |
| `retrieval_attempts`, `search_attempts` | 역주행 카운터 |

레거시 키 `context_body`, `rag_data`, `search_data`는 TypedDict에 없으며 **쓰기 금지**. `get_context_dom` / `get_context_rag` / `get_context_search`가 체크포인트·구버전 state 읽기용 폴백만 제공한다.

Service는 `core/history.py`로 DB 히스토리를 `messages`에 주입한 뒤 `ArchiverEngine.build_initial_state(messages=...)`를 호출한다 (`MAX_HISTORY_MESSAGES=20`).

---

## 4. 상수 SSOT

| 위치 | 상수 | 설명 |
|------|------|------|
| `core/constants.py` | `MAX_SEARCH_ATTEMPTS`, `MAX_RETRIEVAL_ATTEMPTS` | evaluator 역주행 한도 |
| `core/constants.py` | `RAG_SEARCH_LIMIT` | RAG 검색 건수 기본값 |
| `core/constants.py` | `MAX_HISTORY_MESSAGES` | multi-turn 히스토리 상한 |
| `core/constants.py` | `MAX_CONTEXT_BODY_CHARS`, `MIN_CLIENT_CONTEXT_BODY_CHARS`, `MIN_CONTEXT_BODY_QUALITY` | 본문 길이·품질 (익스텐션 `limits.ts`와 수동 동기화) |
| `core/constants.py` | `ARCHIVER_AGENT_TYPE` | DB `ai_chat_logs.agent_type` 필터 |
| `core/constants.py` | `STREAM_ERROR_PREFIX`, `STREAM_ERROR_MESSAGE` | 오류 토큰·DB 미저장 정책 |
| `core/constants.py` | `RESPOND_CHITCHAT_TEMPERATURE`, `RESPOND_FACTUAL_TEMPERATURE` | respond 2단 온도 |
| `core/constants.py` | `GEMINI_MODEL`, classify/evaluate/search temperatures | LLM·스텝 설정 |
| `models/` (`context`, `routing`, `evaluation`, `stream_events`) | `NO_CONTEXT_*`, `RouterTargets`, `Evaluation`, `ArchiverStreamEvent` | 도메인 타입 |
| `prompts/` | `ARCHIVER_*_TEMPLATE` | 프롬프트 본문 |

익스텐션 대응: `extension/src/features/archiver/utils/limits.ts` ↔ `core/constants.py`, `utils/contextBodyQuality.ts` ↔ `utils/context_body_quality.py`.

**TabContext 계약 (OpenAPI SSOT):** `backend/app/schemas/archiver.py` → `shared/openapi.snapshot.json` → `shared/generated/archiver-api.ts` → 익스텐션 `@synapse/shared/archiver-context`. 갱신: `cd extension && pnpm run sync:api-types` ([shared/README.md](../../shared/README.md)).

---

## 5. 인증

모든 Archiver API (`/api/v1/archiver/*`)는 `get_current_user_dep` (Bearer JWT) 필수.

| 엔드포인트 | 설명 |
|------------|------|
| `POST /archiver/stream` | SSE 스트리밍 |
| `GET /archiver/sessions` | 본인 세션 목록 |
| `GET /archiver/history/{session_id}` | 본인 세션 히스토리 (`user_id` 필터) |

익스텐션: `extension/src/shared/api/client.ts` — `getAuthHeaders()`가 `chrome.storage` 토큰 또는 `/auth/extension-refresh`로 Bearer를 갱신한다. OAuth 진입은 `features/auth/services/extensionOAuth.ts`.

---

## 6. 스트리밍 · DB 무결성

### 6.1 파이프라인

```
steps/* · nodes/*  get_stream_writer()
    → Engine  stream_mode=["custom","values"]
    → Service  protocols/streaming.format_stream_event()  (SSE envelope)
    → Extension  archiverClient.ts streamArchiverMessage()
```

### 6.2 SSE 포맷 (`protocols/streaming.py`)

```
event: status
data: {"content": "🔀 [Router] ...\n\n"}

event: token
data: {"content": "답변 토큰"}
```

### 6.3 DB 저장 정책 (`archiver_service.py`)

| 이벤트 | SSE 클라이언트 | `ai_chat_logs` assistant |
|--------|----------------|--------------------------|
| `status` | ✅ 전달 | ❌ 저장 안 함 |
| `token` | ✅ 전달 | ✅ token만 합본 저장 |

`should_persist_assistant_log()` — `STREAM_ERROR_PREFIX`(❌)로 시작하는 오류 토큰은 DB에 남기지 않는다.

---

## 7. RAG (hybrid 검색)

`ArchiverRepository.search_past_knowledge()` — `retrieval_attempt`에 따라 전략 분기.

| 시도 | 전략 |
|------|------|
| 1차 (`retrieval_attempt <= 1`) | 키워드 ILIKE (`past_knowledge/retrieval.extract_search_keywords`) |
| 2차+ (evaluator `collect` 역주행) | pgvector cosine 유사도 → 미스 시 relaxed 전체 쿼리 ILIKE |

**임베딩**

- 저장: `save_chat_log` 시 `[context_title]\ncontent` → `content_embedding` (OpenAI `text-embedding-3-small`, `OPENAI_API_KEY` 없으면 skip)
- 검색: `past_knowledge/embedding.py` — `embed_text_safe()`, `expand_rag_query()`
- orchestration: `past_knowledge/retrieval.py` — `search_past_knowledge()` (`nodes/rag.py`는 Store Port만 호출)

**DB**

- `005_create_ai_chat_logs` — `ai_chat_logs` 테이블 (`user_id UUID → users.id`, `content_embedding vector(1536)` + HNSW 인덱스)

---

## 8. Import 규칙

| From → To | 허용 |
|-----------|------|
| `api/` → `services/`, `schemas/` | ✅ |
| `services/` → `agents/archiver/`, `repositories/` | ✅ |
| `repositories/` → `agents/archiver/past_knowledge/`, `core/constants`, `core/store`, `models/`, `schemas/` | ✅ |
| `agents/archiver/` → `repositories/` | ❌ |
| `agents/archiver/steps/` · `nodes/` → `models`, `core/`, `protocols/`, `trace/` | ✅ |
| `prompts/` → `models` | ✅ |
| `schemas/` → `agents/` | ❌ |

---

## 9. Observability

### 9.1 개발 trace (`trace/`)

box-drawing·이모지 포함 `logger.info` (로컬 디버깅용).

### 9.2 운영 JSON (`trace/observability.py`)

로그 수집기 파싱용 **한 줄 JSON**.

**요청 1건 요약 (`workflow.end`):**

| 필드 | 설명 |
|------|------|
| `session_id` | 대화 세션 |
| `route` | trace 라벨 (`format_router_trace_label`: `general` 또는 `engine+engine`) |
| `eval_score` | evaluator 점수 (0–100) |
| `rag_hit` | RAG 데이터 존재 여부 |
| `search_loops` | search 역주행 횟수 |
| `latency_ms` | 엔진 전체 소요 시간 |

---

## 10. Repository

`app/repositories/archiver_repository.py` — `ArchiverStore` 구현. 상세는 [repositories/README.md](../../backend/app/repositories/README.md).

---

## 11. 테스트 (`backend/scripts/archiver/`)

pytest 없이 `uv run python scripts/archiver/run_archiver_tests.py`로 일괄 실행.

| 스크립트 | 범위 |
|----------|------|
| `archiver/run_archiver_tests.py` | 위 전체 러너 (진입점) |
| `archiver/archiver_test_unit.py` | branches, trace 라벨, Evaluation.fallback |
| `archiver/archiver_test_service.py` | token 격리, `should_persist_assistant_log` |
| `archiver/archiver_smoke.py` | Mock LLM 4경로 (`is_general` + `target_engines`) |
| `archiver/archiver_test_p2.py` | SSE, multi-turn, respond synthesis·tool binding |

`scripts/archiver/README.md` — 개별 실행·범위 요약.

```powershell
cd backend
$env:PYTHONPATH="."
uv run python scripts/archiver/run_archiver_tests.py
```

---

## 12. 디렉터리 구조

```
backend/app/agents/archiver/
├── engine.py
├── workflow.py
├── branches.py
├── core/
│   ├── constants.py
│   ├── store.py
│   ├── history.py
│   └── tools.py
├── models/
│   ├── state.py
│   ├── context.py
│   ├── routing.py
│   ├── evaluation.py
│   └── stream_events.py
├── steps/
│   ├── classify.py
│   ├── evaluate.py
│   ├── respond.py
│   ├── respond_context.py
│   └── need_dom.py
├── nodes/
│   ├── collect.py
│   ├── rag.py              # rag_node (Store Port)
│   ├── search.py
│   └── utils/
│       └── scraper.py
├── past_knowledge/
│   ├── embedding.py
│   └── retrieval.py
├── protocols/
│   ├── streaming.py
│   └── stream_status.py
├── trace/
├── utils/
└── prompts/

backend/app/services/archiver_service.py
backend/app/api/v1/archiver.py
backend/app/repositories/archiver_repository.py
backend/app/models/chat.py                    # AIChatLog

extension/src/
├── entries/
│   ├── content-archiver.ts                   # all_frames Archiver bridge (no React)
│   └── content-tracking.tsx                  # top-frame FAB + auth bridge
├── features/chat/hooks/useChat.ts
├── features/archiver/
│   ├── useArchiver.ts
│   ├── services/archiverClient.ts            # REST + SSE 파싱 SSOT
│   ├── services/queryTabContext.ts           # TabContext public API
│   ├── services/contextBuilder.ts            # ActiveTabInfo → TabContext
│   ├── services/frameCollect.ts              # 멀티프레임 DOM 수집
│   ├── services/tabQuery.ts                  # 활성 Chrome 탭 조회
│   ├── services/domCache.ts                  # 탭별 DOM TTL 캐시
│   └── content/
│       ├── extractVisiblePageText.ts         # 안정화 + 스냅샷 + 채점 오케스트레이션
│       ├── strategies.ts                     # 다중 추출 전략
│       ├── domSafe.ts, domStability.ts, scoring.ts, …
├── features/tracking/content/                # mountFloatingWidget, bootTrackingContent
├── features/scrap/                           # Scrap 탭 — local storage only, Archiver 무연결 (README §Scrap)
└── features/archiver/utils/
    ├── limits.ts                             # ↔ core/constants.py
    └── contextBodyQuality.ts                 # ↔ utils/context_body_quality.py

shared/
├── openapi.snapshot.json                       # OpenAPI codegen 입력 (export_openapi.py)
├── generated/archiver-api.ts                   # 자동 생성 TS (직접 수정 금지)
└── archiver-context.ts                         # TabContext re-export SSOT

backend/alembic/versions/
├── 005_create_ai_chat_logs.py
└── 006_extension_auth.py
```

---

## 13. 장기 후보

| 항목 | 설명 |
|------|------|
| RAG 쿼리 확장 LLM화 | 현재 토큰 join — 동의어·의도 확장 |
| SSE status 전용 UI | status를 답변 버블과 분리 표시 |
| 임베딩 백필 배치 | 기존 로그에 `content_embedding` 소급 생성 |
