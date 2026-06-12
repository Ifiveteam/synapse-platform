# Profiler — 구현·아키텍처

> **일자:** 2026-06-11  
> **상태:** 현재 코드 기준  
> **도메인 스펙:** [SYNAPSE_8.md](./SYNAPSE_8.md)

---

## 1. 레이어 개요

```text
┌─────────────────────────────────────────────────────────────┐
│  app/api/v1/profiler.py          HTTP 라우터 (얇은 어댑터)   │
│       │ 검증 · response_model 변환 · BackgroundTasks         │
│       ▼                                                      │
│  app/schemas/profiler.py         Pydantic — API 요청·응답   │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  app/services/profiler/          Profiler 전용 비즈니스      │
│    service.py    job · run_profiler · 스냅샷 저장/조회       │
│    compare.py    스냅샷 전후 비교 · 이상 징후                 │
│    graph_view.py records → 그래프 뷰 JSON                    │
└─────────────────────────────────────────────────────────────┘
       │ run_profiler()                    │ mock_loader (임시)
       ▼                                   ▼
┌──────────────────────────┐    ┌─────────────────────────────┐
│  app/agents/profiler/    │    │  scripts/mock_loader.py      │
│    graph.py  LangGraph   │    │  (Indexer 전 mock records)   │
│    nodes/    파이프라인   │    └─────────────────────────────┘
│    tools.py  집계·tool   │
│    prompt.py LLM 프롬프트  │
│    base/     도메인 모델  │
│    state/    실행 상태    │
│    scripts/  mock·CLI     │
└──────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  app/services/notification.py, email.py   공용 인프라       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  app/models/                     SQLAlchemy ORM (미사용)     │
│  ※ 프로필·스냅샷은 mocks/snapshots JSON — DB 도입 시 교체   │
└─────────────────────────────────────────────────────────────┘
```

**호출 방향:** `api` → `services/profiler` → `agents/profiler/graph`  
에이전트는 `api`·`services/profiler`를 import하지 않는다.

---

## 2. 레이어별 책임

### 2.1 `agents/profiler/base/` — 도메인 모델 (Pydantic)

에이전트·서비스·내부 계약. HTTP·DB에 종속되지 않는다.

| 파일 | 타입·역할 |
|------|-----------|
| `axes.py` | `Synapse8Axes`, `SYNAPSE_AXIS_KEYS`, `AxesDelta` |
| `layer_b.py` | `LayerB`, `LayerBDelta` |
| `profile.py` | `ProfilerResult`, `Top5Interest`, `profiler_result_from_state()` |
| `record.py` | `IndexedRecord`, `IndexedRecordsBundle` |
| `insights.py` | `ProfilerSnapshot`, `ProfileCompareDelta`, `AnomalyItem` |
| `graph.py` | `GraphViewData`, `GraphNode`, `GraphEdge` (시각화 DTO) |
| `job.py` | `JobStatus`, `PersonaInfo` |

**규칙**

- `app/schemas`의 API 전용 모델을 base에서 import하지 않는다.
- `ProfilerResult`는 파이프라인 산출물; HTTP 응답은 `schemas`에서 `ProfilerResultResponse`로 변환.

### 2.2 `agents/profiler/state/` — LangGraph 실행 상태

그래프 실행 중 흘러가는 변수만 정의. 도메인 스키마 정의소가 아니다.

| 타입 | 주요 필드 |
|------|-----------|
| `ProfilerState` | `user_id`, `records`, `layer_b`, `axes`, `summary`, `interpretation`, … (`NotRequired`로 단계별 채움) |

**규칙**

- `base/` 타입을 필드로 참조만 한다.
- API 응답·ORM 타입을 state에 넣지 않는다.

### 2.3 `app/schemas/profiler.py` — HTTP 경계 (Pydantic)

FastAPI `response_model` 및 OpenAPI용.

| 스키마 | 용도 |
|--------|------|
| `AnalyzeRequest` / `AnalyzeResponse` | `POST /analyze` |
| `JobResponse` | `GET /jobs/{id}` |
| `ProfilerResultResponse` | `GET /profile` |
| `SnapshotListResponse` / `SnapshotResponse` | 스냅샷 API |
| `CompareResponse` | `GET /compare` |
| `PersonasResponse` | `GET /personas` |

**규칙**

- 라우터에서 `ProfilerResult.model_dump()` → `ProfilerResultResponse.model_validate()` 로 경계 변환.
- `schemas` → `agents` 역방향 import 금지.

### 2.4 `app/services/profiler/` — Profiler 비즈니스

| 모듈 | 역할 | API |
|------|------|-----|
| `service.py` | job store, `run_profiler` 호출, 스냅샷 I/O, `get_profile` | analyze, jobs, profile, snapshots |
| `compare.py` | 스냅샷 2개 diff, 이상 징후 규칙 | `/compare` |
| `graph_view.py` | taste/knowledge 그래프 nodes·edges | `/graph` |

**에이전트를 호출하는 유일한 서비스 진입점:** `ProfilerService.run_job()` → `run_profiler()`.

스냅샷 저장 경로 (MVP): `agents/profiler/mocks/snapshots/{user_id}/{version}.json`

### 2.5 `app/api/v1/profiler.py` — HTTP 어댑터

- 요청 검증, HTTP 상태 코드, Pydantic 응답 변환만.
- `run_profiler` 직접 호출 없음 — `profiler_service` 경유.
- `mock_loader`는 personas 목록·graph용 records (Indexer 전 임시).

### 2.6 `agents/profiler/scripts/` — mock·로컬 실행

| 파일 | 역할 |
|------|------|
| `mock_loader.py` | mock persona JSON → `IndexedRecordsBundle` (`load_records` 노드도 사용) |
| `run_test.py` | CLI — `run_profiler()` 직접 호출 (api·service 미경유) |

---

## 3. LangGraph 파이프라인

```text
START → load_records → layer_b → profile_llm → interpretation → notify → END
```

| 노드 | 파일 | 역할 |
|------|------|------|
| `load_records` | `nodes/load_records.py` | records 로드 (현재 `mock_loader`) |
| `layer_b` | `nodes/layer_b.py` | Layer B habits, behavior_patterns, `complete_layer_b` |
| `profile_llm` | `nodes/profile_llm.py` | Gemini tool loop + 8축 structured output, fallback |
| `interpretation` | `nodes/interpretation.py` | 규칙 기반 해석 4요소 |
| `notify` | `nodes/notify.py` | 완료 메일 (`services/email`, `notification`) |

루트 모듈: `graph.py`, `tools.py`, `prompt.py`

---

## 4. 데이터 흐름

### 4.1 시연 본선 — analyze

```text
POST /analyze
  api → profiler_service.create_job()
  api → BackgroundTasks(profiler_service.run_job)
  service.run_job()
    → run_profiler(user_id, email)
    → profiler_result_from_state(final)
    → save_snapshot(user_id, result)
    → job 메모리 · _profiles 캐시 갱신
  ← 202 { job_id }

GET /jobs/{id}  → profiler_service.get_job()
GET /profile    → profiler_service.get_profile()  (메모리 → 최신 스냅샷 fallback)
```

### 4.2 LangGraph 단독 (CLI)

```text
run_test → run_profiler() → profiler_result_from_state()
```

### 4.3 스냅샷 비교

```text
GET /compare?from=v1&to=v2
  api → load_snapshot × 2
  api → compare.compute_compare_delta + detect_anomalies
```

### 4.4 그래프 뷰

```text
GET /graph?kind=taste|knowledge
  api → mock_loader.load_mock_bundle()
  api → profiler_service.get_profile()  (taste 시 8축 노드용)
  api → graph_view.build_graph()
```

---

## 5. HTTP API (현재)

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/profiler/analyze` | 비동기 분석 시작 (202) |
| `GET` | `/profiler/jobs/{job_id}` | job 상태·결과 |
| `GET` | `/profiler/profile/{user_id}` | 최신 프로필 |
| `GET` | `/profiler/personas` | mock persona 목록 |
| `GET` | `/profiler/profile/{user_id}/snapshots` | 스냅샷 버전 목록 |
| `GET` | `/profiler/profile/{user_id}/snapshots/{version}` | 스냅샷 단건 |
| `GET` | `/profiler/profile/{user_id}/compare?from=&to=` | axes/layer_b delta + anomalies |
| `GET` | `/profiler/profile/{user_id}/graph?kind=taste\|knowledge` | 시각화 nodes/edges |

**제거됨 (2026-06):** `/ideal-gap`, `/events` — mock 전용 데모, Navigator·수집 파이프라인 미연동.

---

## 6. Import 규칙

| From → To | 허용 |
|-----------|------|
| `api/` → `services/profiler` | ✅ |
| `api/` → `agents/profiler/scripts/mock_loader` | ✅ (personas·graph records, 임시) |
| `api/` → `agents/graph` | ❌ |
| `api/` → `schemas/` | ✅ |
| `services/profiler` → `agents/graph` | ✅ |
| `services/profiler` → `agents/base` | ✅ |
| `services/profiler` → `agents/tools` | ✅ (`graph_view`만) |
| `agents/*` → `api/`, `services/profiler` | ❌ |
| `agents/nodes` → `services/` | ✅ (`notify` → email, notification) |
| `schemas/` → `agents/` | ❌ |

---

## 7. 디렉터리 구조 (현재)

```text
backend/app/
├── api/v1/profiler.py
├── schemas/profiler.py
├── services/
│   ├── notification.py, email.py
│   └── profiler/
│       ├── service.py
│       ├── compare.py
│       └── graph_view.py
└── agents/profiler/
    ├── graph.py
    ├── tools.py
    ├── prompt.py
    ├── base/
    │   ├── axes.py, layer_b.py, profile.py, record.py
    │   ├── insights.py, graph.py, job.py
    │   └── __init__.py
    ├── state/
    │   ├── profiler.py
    │   └── __init__.py
    ├── nodes/
    │   ├── load_records.py, layer_b.py, profile_llm.py
    │   ├── interpretation.py, notify.py
    │   └── __init__.py
    ├── scripts/
    │   ├── mock_loader.py, run_test.py
    │   └── __init__.py
    └── mocks/
        ├── manifest.json, mock_*.json
        └── snapshots/{user_id}/*.json
```

---

## 8. 테스트

```bash
cd backend
uv run python -m app.agents.profiler.scripts.run_test mock_jiyeon
uv run python -m app.agents.profiler.scripts.run_test --all
```

에이전트 파이프라인만 검증. HTTP API는 서버 기동 후 수동 또는 별도 통합 테스트.

---

## 9. 향후 작업

| 항목 | 설명 |
|------|------|
| Indexer 연동 | `load_records` → Indexer API; `mock_loader` 제거 |
| DB 영속 | `service.py` 스냅샷 JSON → `app/models` + repository |
| `ProfilerResult.from_state` | `profiler_result_from_state` 함수 → 클래스 메서드 정리 (선택) |
| Celery 등 | `run_job` 백그라운드 실행체 교체 시 `ProfilerService` 인터페이스 유지 |

---

## 10. 관련 에이전트

| 에이전트 | 관계 |
|----------|------|
| **Indexer** | `IndexedRecord[]` 공급 (현재 mock JSON) |
| **Navigator** | `ProfilerResult` JSON 소비; 이상향 비교는 Navigator 자체 API (`compare_radar`) |

---

## 변경 이력

| 일자 | 내용 |
|------|------|
| 2026-06-11 | `runtime/` 제거, `services/profiler/` 도입, `views` → compare/graph_view 분리, ideal-gap/events API 제거 |
| 2026-06 | A안 리팩토링: nodes 평탄화, profile_llm, scoring/analysis 제거 |
