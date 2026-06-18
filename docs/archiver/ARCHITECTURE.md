# Archiver 아키텍처 · 레이어 경계

활성 탭·과거 아카이브·웹 검색을 조합해 답변하는 Archiver LangGraph 에이전트의 타입·모듈 배치와 observability를 정의한다.

---

## 1. 레이어 개요

```
┌─────────────────────────────────────────────────────────────┐
│  frontend (채팅 UI)                                          │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼──────────────────────────────────┐
│  app/api/v1/archiver.py       HTTP 라우터                    │
│       ▼                                                      │
│  app/services/archiver_service.py   SSE 스트림·메시지 저장   │
│  app/repositories/archiver_repository.py   RAG·대화 영속     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  app/agents/archiver/         LangGraph 자율 루프 에이전트      │
│    engine.py      그래프 정의·ArchiverEngine.stream()        │
│    branches.py    router / evaluator 조건부 분기             │
│    steps/         classify · collect · search · evaluate · respond │
│    trace/         개발용 box-drawing trace                     │
│    observability.py  운영 JSON 1줄 structured log           │
│    constants.py   런타임·DB 상수 SSOT                        │
│    types.py       Route · State · Evaluation · NO_CONTEXT_* │
│    prompts/       프롬프트 템플릿 (types에서 상수 import)     │
│    gemini.py      Gemini 클라이언트·Structured Output        │
│    store.py       RAG Port (ArchiverStore Protocol)          │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. LangGraph 워크플로우

```
START
  → router (classify)
       ├─ GENERAL  → respond → END
       ├─ SEARCH   → search  → evaluator ⇄ (search | collect | respond) → respond → END
       └─ RAG/BASIC → collect → evaluator ⇄ ...
```

조건부 분기는 `branches.py`에 두고, `trace/routing.py` + `observability.py`에서 로그를 기록한다.

---

## 3. 상수 SSOT

| 위치 | 상수 | 설명 |
|------|------|------|
| `constants.py` | `MAX_SEARCH_ATTEMPTS`, `MAX_RETRIEVAL_ATTEMPTS` | evaluator 역주행 한도 |
| `constants.py` | `RAG_SEARCH_LIMIT` | RAG 검색 건수 기본값 |
| `constants.py` | `ARCHIVER_AGENT_TYPE` | DB `ai_chat_logs.agent_type` 필터 |
| `constants.py` | `GEMINI_MODEL`, temperatures, `STREAM_ERROR_MESSAGE` | LLM·스텝 설정 |
| `types.py` | `NO_CONTEXT_*`, `NO_RAG_CONTEXT`, `OFF_TAB_BODY` | 컨텍스트 플레이스홀더 |
| `types.py` | `ArchiverRoute`, `ArchiverState`, `Evaluation` | 도메인 타입 |
| `prompts/` | `ARCHIVER_*_TEMPLATE` | 프롬프트 본문만 (상수는 types import) |

---

## 4. Import 규칙

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

## 5. Observability

### 5.1 개발 trace (`app.agents.archiver.workflow`)

`trace/` — box-drawing·이모지 포함 `logger.info` (로컬 디버깅용).

### 5.2 운영 JSON (`app.agents.archiver.observability`)

`observability.py` — 로그 수집기 파싱용 **한 줄 JSON**.

**요청 1건 요약 (`workflow.end`) — 운영 필수 필드:**

| 필드 | 설명 |
|------|------|
| `session_id` | 대화 세션 |
| `route` | `BASIC` / `RAG` / `SEARCH` / `GENERAL` |
| `eval_score` | evaluator 점수 (0–100, 없으면 생략) |
| `rag_hit` | RAG 데이터 존재 여부 |
| `search_loops` | search 역주행 횟수 |
| `latency_ms` | 엔진 전체 소요 시간 |

```json
{
  "ts": "2026-06-18T12:00:00+00:00",
  "agent": "archiver",
  "event": "workflow.end",
  "session_id": "abc-123",
  "route": "RAG",
  "eval_score": 72,
  "rag_hit": true,
  "search_loops": 1,
  "latency_ms": 3420
}
```

중간 이벤트: `workflow.start`, `node.enter`, `router.branch`, `collect.result`, `evaluator.branch` 등.

### 5.3 SSE (사용자-facing)

`get_stream_writer()` — `status` / `token`. `status`는 DB에 저장하지 않는다.

---

## 6. Repository

`app/repositories/archiver_repository.py` — `ArchiverStore` 구현. 상세는 [repositories/README.md](../../backend/app/repositories/README.md).

---

## 7. 장기 후보 (별도 Epic)

| 항목 | 설명 |
|------|------|
| RAG 벡터 검색 | pgvector / embedding 기반 semantic search |

---

## 8. 디렉터리 구조

```
backend/app/agents/archiver/
├── observability.py
├── constants.py
├── types.py
├── branches.py
├── engine.py
├── steps/
├── trace/
└── prompts/

backend/app/repositories/
└── archiver_repository.py
```
