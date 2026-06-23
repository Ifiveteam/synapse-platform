# Archiver 아키텍처 · 레이어 경계

활성 탭·과거 아카이브·웹 검색을 조합해 답변하는 Archiver LangGraph 에이전트의 타입·모듈 배치·스트리밍·영속성을 정의한다.

---

## 1. 레이어 개요

```
┌─────────────────────────────────────────────────────────────┐
│  extension (사이드패널 채팅 UI)                               │
│    useChat.ts · archiverStream.ts (SSE 파싱)                 │
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
│    engine.py        그래프·ArchiverEngine.stream()           │
│    branches.py      router / evaluator 조건부 분기           │
│    steps/           classify·collect·search·evaluate·respond │
│    streaming.py     SSE 포맷 (event + JSON data)             │
│    rag_embedding.py RAG 임베딩·쿼리 확장                     │
│    trace/           개발용 box-drawing trace                   │
│    observability.py 운영 JSON 1줄 structured log             │
│    constants.py     런타임·DB 상수 SSOT                        │
│    types.py         Route · State · Evaluation · StreamEvent   │
│    prompts/         프롬프트 템플릿                            │
│    gemini.py        Gemini 클라이언트·Structured Output        │
│    store.py         RAG Port (ArchiverStore Protocol)        │
└─────────────────────────────────────────────────────────────┘
```

**제어권 분담**

| 레이어 | 담당 |
|--------|------|
| `ArchiverService` | 세션 resolve, user/assistant 로그 저장, 히스토리→`messages` 조립, SSE 전달 |
| `ArchiverEngine` + `steps/` | 라우팅, 수집, evaluator 루프, respond 스트리밍 |
| `ArchiverRepository` | `ai_chat_logs` CRUD, hybrid RAG (`ArchiverStore` 구현) |

---

## 2. LangGraph 워크플로우

```
START
  → router (classify)
       ├─ GENERAL  → respond → END          ← Fast-Path (collect·evaluator 생략)
       ├─ SEARCH   → search  → evaluator ⇄ (search | collect | respond) → respond → END
       └─ RAG/BASIC → collect → evaluator ⇄ ...
```

조건부 분기는 `branches.py`에 두고, `trace/routing.py` + `observability.py`에서 로그를 기록한다.

### 2.1 GENERAL Fast-Path

`route == GENERAL` → `router → respond → END`. 수집·evaluator·검색 단계를 건너뛴다.

### 2.2 Evaluator 역주행

Gemini 2.5 Flash Structured Output (`Evaluation`)으로 근거 충분성 채점 후:

| 조건 | 다음 노드 |
|------|-----------|
| `is_sufficient` | `respond` |
| `recommended_action=search` & `search_attempts < MAX` | `search` (역주행) |
| `recommended_action=collect` & `retrieval_attempts < MAX` | `collect` (역주행) |
| 한도 초과 | `respond` (best-effort) |

### 2.3 respond Tool 바인딩

`steps/respond_context.py` — Google Search Tool은 **`SEARCH` 경로이면서 `search_data`가 비어 있을 때만** 바인딩한다. evaluator 역주행으로 `search_data`가 채워진 경우 수집 결과만으로 생성한다.

---

## 3. ArchiverState

`types.py` — LangGraph 실행 상태 SSOT.

| 필드 | 설명 |
|------|------|
| `messages` | `add_messages` 리듀서 — **multi-turn 히스토리 포함** |
| `user_id` | `uuid.UUID` (`users.id` FK) |
| `session_id` | 대화 세션 (URL 단위 그룹) |
| `route` | `BASIC` / `RAG` / `SEARCH` / `GENERAL` |
| `context_body`, `rag_data`, `search_data` | 수집 근거 |
| `evaluation_result` | evaluator 채점 JSON |
| `retrieval_attempts`, `search_attempts` | 역주행 카운터 |

Service는 `history.py`로 DB 히스토리를 `messages`에 주입한 뒤 `ArchiverEngine.build_initial_state(messages=...)`를 호출한다 (`MAX_HISTORY_MESSAGES=20`).

---

## 4. 상수 SSOT

| 위치 | 상수 | 설명 |
|------|------|------|
| `constants.py` | `MAX_SEARCH_ATTEMPTS`, `MAX_RETRIEVAL_ATTEMPTS` | evaluator 역주행 한도 |
| `constants.py` | `RAG_SEARCH_LIMIT` | RAG 검색 건수 기본값 |
| `constants.py` | `MAX_HISTORY_MESSAGES` | multi-turn 히스토리 상한 |
| `constants.py` | `RAG_EMBEDDING_DIM` | pgvector 차원 (1536) |
| `constants.py` | `ARCHIVER_AGENT_TYPE` | DB `ai_chat_logs.agent_type` 필터 |
| `constants.py` | `STREAM_ERROR_PREFIX`, `STREAM_ERROR_MESSAGE` | 오류 토큰·DB 미저장 정책 |
| `constants.py` | `GEMINI_MODEL`, temperatures | LLM·스텝 설정 |
| `types.py` | `NO_CONTEXT_*`, `Evaluation`, `ArchiverStreamEvent` | 도메인 타입 |
| `prompts/` | `ARCHIVER_*_TEMPLATE` | 프롬프트 본문 |

---

## 5. 인증

모든 Archiver API (`/api/v1/archiver/*`)는 `get_current_user_dep` (Bearer JWT) 필수.

| 엔드포인트 | 설명 |
|------------|------|
| `POST /archiver/stream` | SSE 스트리밍 |
| `GET /archiver/sessions` | 본인 세션 목록 |
| `GET /archiver/history/{session_id}` | 본인 세션 히스토리 (`user_id` 필터) |

익스텐션: `extension/src/shared/api/client.ts` — `getAuthHeaders()`가 `chrome.storage` 토큰 또는 `/auth/dev-login`으로 Bearer를 붙인다.

---

## 6. 스트리밍 · DB 무결성

### 6.1 파이프라인

```
steps/*  get_stream_writer()
    → Engine  stream_mode=["custom","values"]
    → Service  format_stream_event()  (SSE envelope)
    → Extension  parseArchiverSseBuffer()
```

### 6.2 SSE 포맷 (`streaming.py`)

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
| 1차 (`retrieval_attempt <= 1`) | 키워드 ILIKE (`_extract_search_keywords`) |
| 2차+ (evaluator `collect` 역주행) | pgvector cosine 유사도 → 미스 시 relaxed 전체 쿼리 ILIKE |

**임베딩**

- 저장: `save_chat_log` 시 `[context_title]\ncontent` → `content_embedding` (OpenAI `text-embedding-3-small`, `OPENAI_API_KEY` 없으면 skip)
- 검색: `rag_embedding.py` — `embed_text_safe()`, `expand_rag_query()`

**DB**

- `005_create_ai_chat_logs` — `ai_chat_logs` 테이블 (`user_id UUID → users.id`, `content_embedding vector(1536)` + HNSW 인덱스)

---

## 8. Import 규칙

| From → To | 허용 |
|-----------|------|
| `api/` → `services/`, `schemas/` | ✅ |
| `services/` → `agents/archiver/`, `repositories/` | ✅ |
| `repositories/` → `agents/archiver/store`, `constants`, `models/`, `schemas/` | ✅ |
| `agents/archiver/` → `repositories/` | ❌ |
| `agents/archiver/steps/` → `types`, `constants`, `store`, `observability` | ✅ |
| `prompts/` → `types` | ✅ |
| `schemas/` → `agents/` | ❌ |

---

## 9. Observability

### 9.1 개발 trace (`trace/`)

box-drawing·이모지 포함 `logger.info` (로컬 디버깅용).

### 9.2 운영 JSON (`observability.py`)

로그 수집기 파싱용 **한 줄 JSON**.

**요청 1건 요약 (`workflow.end`):**

| 필드 | 설명 |
|------|------|
| `session_id` | 대화 세션 |
| `route` | `BASIC` / `RAG` / `SEARCH` / `GENERAL` |
| `eval_score` | evaluator 점수 (0–100) |
| `rag_hit` | RAG 데이터 존재 여부 |
| `search_loops` | search 역주행 횟수 |
| `latency_ms` | 엔진 전체 소요 시간 |

---

## 10. Repository

`app/repositories/archiver_repository.py` — `ArchiverStore` 구현. 상세는 [repositories/README.md](../../backend/app/repositories/README.md).

---

## 11. 테스트 (`backend/scripts/`)

pytest 없이 `uv run python scripts/run_archiver_tests.py`로 일괄 실행.

| 스크립트 | 범위 |
|----------|------|
| `archiver_test_unit.py` | branches, route 파싱, Evaluation.fallback |
| `archiver_test_service.py` | token 격리, `should_persist_assistant_log` |
| `archiver_smoke.py` | Mock LLM 4경로 + evaluator 역주행 |
| `archiver_test_p2.py` | SSE, multi-turn, respond tool binding |
| `run_archiver_tests.py` | 위 전체 러너 |

```powershell
cd backend
$env:PYTHONPATH="."
uv run python scripts/run_archiver_tests.py
```

---

## 12. 디렉터리 구조

```
backend/app/agents/archiver/
├── engine.py
├── branches.py
├── constants.py
├── types.py
├── gemini.py
├── store.py
├── streaming.py
├── rag_embedding.py
├── observability.py
├── steps/
│   ├── classify.py
│   ├── collect.py
│   ├── search.py
│   ├── evaluate.py
│   ├── respond.py
│   ├── respond_context.py
│   ├── history.py
│   ├── rag.py
│   └── scraper.py
├── trace/
└── prompts/

backend/app/services/archiver_service.py
backend/app/api/v1/archiver.py
backend/app/repositories/archiver_repository.py
backend/app/models/chat.py                    # AIChatLog

extension/src/
├── features/chat/hooks/useChat.ts
└── shared/api/archiverStream.ts

backend/alembic/versions/
└── 005_create_ai_chat_logs.py
```

---

## 13. 장기 후보

| 항목 | 설명 |
|------|------|
| RAG 쿼리 확장 LLM화 | 현재 토큰 join — 동의어·의도 확장 |
| SSE status 전용 UI | status를 답변 버블과 분리 표시 |
| 임베딩 백필 배치 | 기존 로그에 `content_embedding` 소급 생성 |
