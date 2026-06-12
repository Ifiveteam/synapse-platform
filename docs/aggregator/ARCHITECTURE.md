# Aggregator 아키텍처 · 레이어 경계

Aggregator 에이전트의 타입·모듈 배치 원칙과 각 레이어의 책임을 정의한다.

> **범위:** `profiler/base/axes` 8축 SSOT 통합은 별도 작업으로 보류한다.  
> 현재 8축 정의는 `mock_data.py`, `prompts.py`에 로컬로 유지한다.

---

## 1. 레이어 개요

```
┌─────────────────────────────────────────────────────────────┐
│  app/api/v1/trend.py          HTTP 라우터 (얇은 어댑터)      │
│       │ Depends / 변환                                       │
│       ▼                                                      │
│  app/schemas/trend.py         Pydantic — API 요청·응답       │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  app/agents/aggregator/       에이전트 파이프라인            │
│    agent.py      진입점 (리포트 · run)                       │
│    pipeline.py   통합 데이터 조립                            │
│    base/         도메인 TypedDict (내부 계약)                  │
│    state/        LangGraph 실행 상태                         │
│    nodes.py      그래프 노드 함수                            │
│    graph.py      LangGraph 오케스트레이션                    │
│    report.py     Gemini 리포트 생성                          │
│    mock_data.py  Mock 데이터 생성기                          │
│    prompts.py    LLM 프롬프트                                │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  app/services/external_trends.py   외부 트렌드 fetch DTO     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  app/models/                  SQLAlchemy ORM (DB 도입 시)   │
│  ※ 현재 trend 게시판은 인메모리 — models 미사용             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 레이어별 책임

### 2.1 `aggregator/base/` — 파이프라인 내부 도메인 (TypedDict)

에이전트·LLM·LangGraph가 공유하는 **데이터 계약**. FastAPI나 DB에 종속되지 않는다.

| 파일 | 타입 |
|------|------|
| `internal_stats.py` | `KeywordStat`, `ProfileAxisScore`, `CognitiveProfileMap`, `InternalUserStats` |
| `integrated.py` | `IntegratedData`, `INTEGRATED_SCHEMA_VERSION` |

**규칙**

- TypedDict만 사용 (Profiler state와 동일한 스타일).
- `app/schemas`의 Pydantic 모델을 import하지 않는다.
- HTTP·ORM 타입을 base에 넣지 않는다.

### 2.2 `aggregator/state/` — LangGraph 실행 상태

그래프 실행 중 **흘러가는 변수**만 정의한다. 도메인 스키마 정의소가 아니다.

| 타입 | 필드 |
|------|------|
| `AggregatorState` | `integrated_data`, `report_markdown`, `error` (모두 optional) |

**규칙**

- `base/`의 도메인 타입을 필드 타입으로 **참조**만 한다.
- API 응답 모델, DB ORM을 state에 넣지 않는다.

### 2.3 `app/schemas/trend.py` — HTTP 경계 (Pydantic)

FastAPI `response_model` 및 OpenAPI 문서용.

| 스키마 | 용도 |
|--------|------|
| `KeywordStatSchema`, `ProfileAxisSchema` | 대시보드·그래프 필드 |
| `DashboardResponse`, `GraphViewResponse` | GET 응답 |
| `TrendPostResponse`, `TrendPostListResponse` | 게시판 API |
| `AnalyzeResponse` | POST `/analyze` |

**규칙**

- aggregator `base/` TypedDict를 **직접 response_model로 쓰지 않는다**.
- 라우터에서 `ProfileAxisSchema.model_validate(axis)` 등으로 **경계에서 변환**한다.
- agent 내부 TypedDict와 필드명이 유사해도 **의도적 이중 정의**로 유지한다 (경계 분리).

### 2.4 `app/models/` — DB 영속 (현재 미사용)

README 기준 **SQLAlchemy ORM 전용**.

- trend 게시판은 `_TREND_POSTS` 인메모리 dict로 운영 중.
- PostgreSQL 등 DB 도입 시에만 `TrendPost` ORM 등을 추가한다.
- `IntegratedData` 같은 LLM 입력용 TypedDict는 models에 넣지 않는다.

### 2.5 `app/services/external_trends.py` — 외부 fetch DTO

Google Trends, YouTube, Naver 등 **외부 API 수집 결과** TypedDict.

- `ExternalMarketTrends`는 `IntegratedData.external_market_trends` 필드 타입으로 참조된다.
- HTTP에 그대로 노출하지 않으면 schemas로 옮기지 않는다.

### 2.6 `app/api/v1/trend.py` — HTTP 어댑터

**얇게 유지:** 비즈니스 로직·데이터 조립은 aggregator에 위임한다.

| 책임 | 위치 |
|------|------|
| 데이터 조립 | `aggregator.pipeline.assemble_integrated_data()` |
| 리포트 생성 | `aggregator.agent.AggregatorAgent.generate_report()` |
| 인메모리 게시판 | `TrendPostRecord` (라우터 private TypedDict) |
| Pydantic 변환 | `_to_post_response()` 등 helper |

---

## 3. 모듈별 역할 (aggregator 내부)

| 모듈 | 역할 |
|------|------|
| `pipeline.py` | `assemble_integrated_data()` — 내부 Mock + 외부 트렌드 조립 |
| `agent.py` | 외부 진입점. `AggregatorAgent`, `get_aggregator_agent()` |
| `graph.py` | `assemble_data` → `generate_report` LangGraph 정의 |
| `nodes.py` | 노드 함수만 (`assemble_data_node`, `generate_report_node`) |
| `report.py` | Gemini 클라이언트·모델 fallback·`generate_b2b_report()` |
| `mock_data.py` | Mock 내부 통계 생성 (`generate_internal_user_stats`) |
| `prompts.py` | 시스템·유저 프롬프트, Markdown 리포트 템플릿 |

---

## 4. 데이터 흐름

### 4.1 대시보드 GET `/dashboard`

```
assemble_integrated_data()
  → IntegratedData (base/)
  → generate_b2b_report()
  → trend.py: KeywordStatSchema.model_validate(...)
  → DashboardResponse (schemas/)
  → JSON
```

### 4.2 LangGraph 전체 실행

```
AggregatorAgent.run()
  → graph: START → assemble_data → generate_report → END
  → AggregatorState (state/)
```

### 4.3 POST `/analyze` (게시판)

```
AggregatorAgent.assemble_integrated_data()
  → AggregatorAgent.generate_report()
  → TrendPostRecord (라우터 private, 인메모리)
  → TrendPostResponse (schemas/, 조회 시)
```

---

## 5. Import 규칙

| From → To | 허용 |
|-----------|------|
| `api/` → `aggregator/` | ✅ (agent, base) |
| `api/` → `schemas/` | ✅ |
| `aggregator/base/` → `schemas/` | ❌ |
| `aggregator/base/` → `api/` | ❌ |
| `aggregator/state/` → `aggregator/base/` | ✅ |
| `aggregator/nodes/` → `agent`, `report`, `state` | ✅ |
| `schemas/` → `aggregator/` | ❌ (역방향 금지) |

---

## 6. 향후 작업 (별도 PR)

| 항목 | 설명 |
|------|------|
| 8축 SSOT | `profiler/base/axes.py` 참조로 `mock_data`, `prompts` 중복 제거 |
| DB 영속 | `app/models/TrendPost` + repository, `TrendPostRecord` 제거 |
| sub_agent | 키워드 교차분석·격차 스코어링 등 노드 분리 시 `sub_agent/` 활용 |

---

## 7. 디렉터리 구조 (현재)

```
backend/app/agents/aggregator/
├── base/
│   ├── __init__.py
│   ├── integrated.py
│   └── internal_stats.py
├── state/
│   ├── __init__.py
│   └── aggregator.py
├── sub_agent/          # placeholder (향후 확장)
├── agent.py
├── pipeline.py
├── graph.py
├── nodes.py
├── report.py
├── mock_data.py
└── prompts.py
```
