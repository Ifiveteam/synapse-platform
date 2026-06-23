# Aggregator 아키텍처 · 레이어 경계

B2B 트렌드·미디어 인텔리전스 Aggregator 에이전트의 타입·모듈 배치 원칙과 데이터 흐름을 정의한다.

> **범위:** `profiler/base/axes` 8축 SSOT 통합은 별도 작업으로 보류한다.  
> 현재 8축 정의는 `mock_data.py`, `prompts/shared.py`에 로컬로 유지한다.

---

## 1. 레이어 개요

```
┌─────────────────────────────────────────────────────────────┐
│  frontend/lib/api/trend.ts    분석·게시글 API 클라이언트      │
│  frontend/components/aggregator/  대시보드 UI                │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────────┐
│  app/api/v1/trend.py          HTTP 라우터 (얇은 어댑터)      │
│       ▼                                                      │
│  app/services/trend/          게시판·mapper·PDF              │
│  app/schemas/trend.py         Pydantic — API 요청·응답       │
│  app/schemas/report.py        DashboardReportSchema (리포트) │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  app/agents/aggregator/       LangGraph 멀티 에이전트        │
│    agent.py      진입점 (run / run_assemble_only)            │
│    graph.py      전체 그래프 + 경량 조립 서브그래프            │
│    nodes/        LangGraph 노드 (assemble·culture·market…)   │
│    trace/        워크플로우·노드·라우팅 trace              │
│    routing.py    Critique 루프 조건부 분기                   │
│    pipeline.py   통합 데이터 조립                            │
│    llm/gemini.py Gemini 클라이언트·Structured Output         │
│    report/       generator · markdown                        │
│    prompts/      culture · market · master · verify         │
│    sub_agent/    culture · market · verify 서브 에이전트     │
│    state/        AggregatorState · RevisionTarget SSOT       │
│    base/         IntegratedData 등 파이프라인 내부 계약       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  app/services/external_trends.py   외부 트렌드 fetch         │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. LangGraph 워크플로우

### 2.1 전체 그래프 (`build_aggregator_graph`)

```
START
  → assemble_data          # 내부 Mock + 외부 fetch (Gemini 미호출)
  → culture_analysis  ─┐   # 병렬 Map
  → market_analysis   ─┤
                       ├→ generate_report   # 마스터 융합 → DashboardReportSchema
                       └→ verify_report     # 시니어 검수 (0~100점)
                            ├─ score ≥ 80 또는 review_count ≥ 3 → notify → END
                            └─ 미달 → revision_target에 따라 역주행
                                 · generate_report
                                 · culture_analysis
                                 · market_analysis
                                 · both_analyses (Send 병렬)
```

상수: `REVIEW_PASS_THRESHOLD = 80`, `MAX_REVIEW_ATTEMPTS = 3` (`state/aggregator.py`)

### 2.2 경량 서브그래프 (`build_data_assembly_graph`)

```
START → assemble_data → END
```

`AggregatorAgent.run_assemble_only()` 진입점. Gemini 호출 없이 `integrated_data`만 조립한다.  
향후 차트 전용 API 등 경량 엔드포인트에서 재사용할 수 있다.

---

## 3. API 엔드포인트

프론트엔드는 **게시판(post_id) 중심** 흐름만 사용한다. 분석 결과는 `POST /analyze` 시 인메모리 저장 후 조회한다.

| Method | Path | 설명 | LangGraph |
|--------|------|------|-----------|
| `POST` | `/analyze` | 전체 분석 실행 + 게시글 저장 | 전체 그래프 |
| `GET` | `/posts` | 게시글 목록 | — |
| `GET` | `/posts/{post_id}` | 게시글 상세 (axes + report JSON) | — |
| `GET` | `/posts/{post_id}/download` | 저장된 리포트 PDF | — |

> **제거됨 (P0):** `GET /dashboard`, `GET /download-pdf` — 요청마다 전체 그래프를 재실행하는 비용 함정이었음.  
> `GET /graph` — 프론트 미사용. 차트 데이터는 `GET /posts/{post_id}`의 `report.radar_chart_data`로 충분.

---

## 4. 레이어별 책임

### 4.1 `aggregator/base/` — 파이프라인 내부 도메인 (TypedDict)

| 파일 | 타입 |
|------|------|
| `internal_stats.py` | `KeywordStat`, `ProfileAxisScore`, `CognitiveProfileMap`, `InternalUserStats` |
| `integrated.py` | `IntegratedData`, `INTEGRATED_SCHEMA_VERSION` |

- `app/schemas` Pydantic 모델을 import하지 않는다.

### 4.2 `aggregator/state/` — LangGraph 실행 상태

| 필드 | 설명 |
|------|------|
| `integrated_data` | 조립된 통합 데이터 |
| `culture_analysis` / `market_analysis` | 서브 에이전트 Markdown 초안 |
| `report_json` | 마스터 융합 `DashboardReportSchema` |
| `verification_score` / `critique_feedback` / `revision_target` / `review_count` | Critique 루프 |
| `notify_email` / `post_id` / `notification` | 알림·게시판 연동 |

### 4.3 `app/schemas/report.py` — 리포트 Structured Output

`DashboardReportSchema` 및 하위 모델. Gemini `json_schema` 강제 출력·프론트 대시보드 바인딩 SSOT.

### 4.4 `app/schemas/trend.py` — HTTP 경계

| 스키마 | 용도 |
|--------|------|
| `TrendPostResponse`, `TrendPostListResponse` | 게시판 API (`report` JSON 포함) |
| `AnalyzeRequest`, `AnalyzeResponse` | `POST /analyze` |

8각 축 데이터는 `TrendPostResponse.report.radar_chart_data`로만 제공한다.

### 4.5 `app/services/trend/` — 게시판·PDF 서비스

| 모듈 | 역할 |
|------|------|
| `repository.py` | 인메모리 게시판 CRUD |
| `mapper.py` | `AggregatorState` → `TrendPostRecord` → Pydantic |
| `pdf.py` | `build_trend_report_pdf()` — Markdown·PDF 변환 통합 |
| `types.py` | `TrendPostRecord` |

### 4.6 `app/api/v1/trend.py` — HTTP 어댑터

라우트 정의만 담당. 비즈니스 로직은 `services/trend/`에 위임한다.

---

## 5. 모듈별 역할 (aggregator 내부)

| 모듈 | 역할 |
|------|------|
| `agent.py` | `run()`, `run_assemble_only()` 외부 진입점 |
| `graph.py` | LangGraph 정의·컴파일 |
| `nodes/` | `assemble`, `culture`, `market`, `generate`, `verify`, `notify` 노드 |
| `trace/` | `workflow`, `nodes`, `routing` 단계별 로깅 |
| `routing.py` | `route_after_verify`, Critique 피드백 주입 헬퍼 |
| `pipeline.py` | `assemble_integrated_data()` |
| `llm/gemini.py` | Gemini 호출·fallback·Structured Output |
| `report/generator.py` | `generate_fused_b2b_report()` |
| `report/markdown.py` | `coerce_dashboard_report()`, PDF용 Markdown |
| `prompts/` | 에이전트별 프롬프트 (`culture`, `market`, `master`, `verify`) |
| `state/types.py` | `RevisionTarget`, `REVIEW_PASS_THRESHOLD` SSOT |
| `sub_agent/` | `culture`, `market`, `verify` LLM 호출 |
| `notify.py` | 이메일·PDF 첨부 노드 |
| `mock_data.py` | Mock 내부 통계 생성 |

---

## 6. 데이터 흐름 (E2E)

### 6.1 분석 실행 → 대시보드

```
AggregatorAnalyzeButton
  → POST /analyze (선택 email)
  → agent.run() → LangGraph 전체
  → services/trend/repository 저장
  → { post_id }
  → GET /posts/{post_id}
  → TrendPostDashboard (report JSON 직접 바인딩)
```

### 6.2 PDF 다운로드

```
TrendPostDashboard
  → GET /posts/{post_id}/download
  → services/trend/pdf.build_trend_report_pdf()
```

---

## 7. Import 규칙

| From → To | 허용 |
|-----------|------|
| `api/` → `aggregator/` | ✅ |
| `api/` → `schemas/` | ✅ |
| `aggregator/base/` → `schemas/` | ❌ |
| `aggregator/state/` → `aggregator/base/` | ✅ |
| `schemas/` → `aggregator/` | ❌ |

---

## 8. 향후 작업 (별도 PR)

| 항목 | 설명 |
|------|------|
| 8축 SSOT | `profiler/base/axes.py` 참조로 `mock_data`, `prompts/shared` 중복 제거 |
| DB 영속 | `app/models/TrendPost` + repository, 인메모리 `repository.py` 교체 |
| 단위 테스트 | `routing.py`, `VerificationResult.resolve_revision_target` |

---

## 9. 디렉터리 구조 (현재)

```
backend/app/agents/aggregator/
├── base/
├── state/
│   ├── aggregator.py
│   └── types.py          # RevisionTarget SSOT
├── llm/
│   └── gemini.py
├── report/
│   ├── generator.py
│   └── markdown.py
├── prompts/
│   ├── culture.py
│   ├── market.py
│   ├── master.py
│   ├── verify.py
│   └── shared.py
├── sub_agent/
├── nodes/
│   ├── assemble.py
│   ├── culture.py
│   ├── market.py
│   ├── generate.py
│   ├── verify.py
│   └── notify.py
├── trace/
│   ├── workflow.py
│   ├── nodes.py
│   └── routing.py
├── agent.py
├── graph.py
├── routing.py
├── pipeline.py
└── mock_data.py

backend/app/services/trend/
├── repository.py
├── mapper.py
├── pdf.py
└── types.py

frontend/components/aggregator/
├── aggregator-actions.tsx
├── aggregator-analyze-button.tsx
├── cognitive-obsidian-graph.tsx
├── trend-gap-dashboard.tsx
├── trend-post-dashboard.tsx
└── trend-post-list.tsx
```
