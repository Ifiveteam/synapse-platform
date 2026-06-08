# Aggregator Agent MVP 개발 문서

> **작성 목적:** Synapse Platform 프로젝트를 처음 접하는 개발자·기획자가, Aggregator(어그리게이터) 에이전트 백엔드 MVP의 배경·구조·사용법을 이해할 수 있도록 정리한 문서입니다.  
> **브랜치:** `feature/aggregator`  
> **스키마 버전:** `0.2.0`

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [Multi-Agent System 구조](#2-multi-agent-system-구조)
3. [Aggregator 에이전트란?](#3-aggregator-에이전트란)
4. [이번 MVP에서 구현한 범위](#4-이번-mvp에서-구현한-범위)
5. [기술 스택](#5-기술-스택)
6. [백엔드 아키텍처 (Layered Architecture)](#6-백엔드-아키텍처-layered-architecture)
7. [디렉터리 구조](#7-디렉터리-구조)
8. [핵심 모듈 상세](#8-핵심-모듈-상세)
9. [데이터 스키마](#9-데이터-스키마)
10. [8각 인지 성향 차트 (프로파일러 공통 스키마)](#10-8각-인지-성향-차트-프로파일러-공통-스키마)
11. [Gemini 리포트 생성 파이프라인](#11-gemini-리포트-생성-파이프라인)
12. [REST API 명세](#12-rest-api-명세)
13. [환경 변수 설정](#13-환경-변수-설정)
14. [로컬 실행 방법](#14-로컬-실행-방법)
15. [데이터 흐름 다이어그램](#15-데이터-흐름-다이어그램)
16. [아직 구현되지 않은 항목 (향후 작업)](#16-아직-구현되지-않은-항목-향후-작업)
17. [프론트엔드 연동 가이드](#17-프론트엔드-연동-가이드)

---

## 1. 프로젝트 개요

**Synapse Platform**은 크롬 익스텐션을 통해 사용자의 **시청·검색·스크랩 데이터**를 안전하게 수집하고, 5개의 AI 에이전트가 협력하여 사용자의 **필터 버블(편향된 알고리즘 피드)** 을 변형·확장해 주는 **Multi-Agent System**입니다.

| 구분 | 설명 |
|------|------|
| **수집 계층** | 크롬 익스텐션 → 사용자 디지털 행동 데이터 수집 |
| **에이전트 계층** | 5개 가상 에이전트가 각자 역할에 맞게 데이터 처리 |
| **서비스 계층** | FastAPI 백엔드 + Next.js 프론트엔드 |
| **목표** | 개인의 정보 편식을 완화하고, 더 균형 잡힌 미디어 소비 경험 제공 |

현재 이 문서가 다루는 범위는 5개 에이전트 중 **Aggregator(어그리게이터)** 의 백엔드 MVP입니다.

---

## 2. Multi-Agent System 구조

플랫폼에는 5개의 에이전트가 존재하며, 각각 B2C(개인) 또는 B2B(시장) 관점에서 동작합니다.

| 에이전트 | ID | 역할 | 관점 |
|----------|-----|------|------|
| **Archiver** | `archiver` | 사용자가 의도적으로 수집한 지식을 내재화하고 토론하는 지적 동반자 | B2C |
| **Indexer** | `indexer` | 무의식적 디지털 발자국을 기록·정돈하는 기억 저장소 | B2C |
| **Profiler** | `profiler` | 데이터를 통해 사용자 성향을 비춰주는 분석가 | B2C |
| **Navigator** | `navigator` | 사용자가 이상향으로 나아가도록 이끄는 페이스메이커 | B2C |
| **Aggregator** | `aggregator` | 비식별 데이터 + 외부 트렌드를 통합해 **매크로 트렌드 리포트**를 생산 | **B2B** |

```
┌─────────────────────────────────────────────────────────────┐
│                    크롬 익스텐션 (데이터 수집)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
     ┌─────────────────────┼─────────────────────┐
     ▼                     ▼                     ▼
 ┌─────────┐         ┌───────────┐         ┌───────────┐
 │ Indexer │         │ Profiler  │         │ Archiver  │  ... B2C
 └────┬────┘         └─────┬─────┘         └───────────┘
      │                    │
      │  비식별 집계 데이터   │  8각 성향 지표
      └────────┬───────────┘
               ▼
        ┌─────────────┐
        │ Aggregator  │  ← B2B 매크로 트렌드 리포트
        └──────┬──────┘
               ▼
        ┌─────────────┐
        │  REST API   │ → 프론트엔드 대시보드
        └─────────────┘
```

---

## 3. Aggregator 에이전트란?

다른 에이전트가 **개인(B2C)** 관점에서 동작한다면, Aggregator는 **시장(B2B)** 관점에서 동작하는 핵심 비즈니스 레이어입니다.

### 하는 일

1. **내부 데이터:** 플랫폼 전체 유저의 비식별화된 행동 통계 (상위 키워드 빈도, 8각 성향 평균 분포)
2. **외부 데이터:** Google Trends, YouTube 급상승 등 시장 트렌드 (현재는 Mock)
3. **AI 분석:** Gemini가 내부·외부 데이터의 **격차(Gap)** 를 분석하고 **미디어 중립성**을 평가
4. **산출물:** B2B 매크로 트렌드 리포트 (Markdown) → 대시보드 게시 / PDF 다운로드 (PDF는 향후)

### MVP 전략

타 에이전트의 실제 데이터 스키마가 아직 확정되지 않았기 때문에, **`mock_data.py`의 가상 데이터**로 파이프라인 전체를 독립적으로 구동할 수 있게 구축했습니다.

```
[Mock 데이터 생성] → [Gemini 트렌드 분석] → [Markdown 리포트] → [REST API → 프론트]
```

---

## 4. 이번 MVP에서 구현한 범위

| 영역 | 구현 내용 | 상태 |
|------|-----------|------|
| Mock 데이터 | 비식별 유저 통계 + 외부 트렌드 가상 JSON 생성 | ✅ 완료 |
| AI 프롬프트 | B2B 분석가 페르소나 + Markdown 리포트 템플릿 | ✅ 완료 |
| Gemini 연동 | `gemini-2.5-flash` 기반 리포트 생성 | ✅ 완료 |
| LangGraph 노드 | `generate_report_node()` (graph.py 연동 준비) | ✅ 베이스라인 |
| Pydantic 스키마 | API 응답 모델 정의 | ✅ 완료 |
| REST API | 대시보드 / 8각 차트 엔드포인트 | ✅ 완료 |
| FastAPI 앱 | `app/main.py` 진입점 | ✅ 완료 |
| LangGraph 워크플로 | `graph.py`, `state.py` | ⏳ 미구현 |
| PDF 다운로드 | HTML → PDF 변환 | ⏳ 미구현 |
| 실데이터 연동 | 타 에이전트 스키마 연결 | ⏳ 미구현 |
| 프론트엔드 UI | 대시보드·차트 컴포넌트 | ⏳ 미구현 |

---

## 5. 기술 스택

| 항목 | 기술 | 버전 (대략) |
|------|------|-------------|
| 언어 | Python | 3.12 |
| 패키지 매니저 | uv | - |
| 웹 프레임워크 | FastAPI | 0.136.x |
| ASGI 서버 | Uvicorn | 0.49.x |
| AI 프레임워크 | LangChain + LangGraph | 1.3.x / 1.2.x |
| LLM | Google Gemini (`langchain-google-genai`) | gemini-2.5-flash |
| 스키마 검증 | Pydantic | (FastAPI 내장) |
| 린터 | Ruff | 0.15.x |
| 환경 변수 | python-dotenv | 1.2.x |

---

## 6. 백엔드 아키텍처 (Layered Architecture)

코드는 **역할별 레이어 분리** 원칙을 따릅니다.

```
┌──────────────────────────────────────────────┐
│  api/v1/          REST 라우트 (HTTP 입출력)    │
├──────────────────────────────────────────────┤
│  schemas/         Pydantic 요청·응답 모델      │
├──────────────────────────────────────────────┤
│  services/        결정론적 비즈니스 로직 (향후)  │
├──────────────────────────────────────────────┤
│  agents/aggregator/  AI 추론 (LangGraph·LLM)  │
└──────────────────────────────────────────────┘
```

| 레이어 | 책임 | 이번 MVP 파일 |
|--------|------|---------------|
| **API** | HTTP 엔드포인트, 의존성 주입, 응답 직렬화 | `app/api/v1/trend.py` |
| **Schema** | 프론트엔드와의 계약(Contract) 정의 | `app/schemas/trend.py` |
| **Agent** | Mock 데이터, 프롬프트, Gemini 호출 | `app/agents/aggregator/*` |
| **Main** | FastAPI 앱 생성, 라우터 등록, .env 로드 | `app/main.py` |

**의존성 방향:** `API → Agent` (API가 Agent를 호출, Agent는 API를 모름)

---

## 7. 디렉터리 구조

```
backend/
├── .env                          # 환경 변수 (API 키, Git 제외)
├── pyproject.toml                # 의존성 및 Ruff 설정
├── uv.lock
└── app/
    ├── main.py                   # FastAPI 앱 진입점
    ├── api/
    │   └── v1/
    │       ├── __init__.py       # api_router 집합
    │       └── trend.py          # 트렌드 API 라우터
    ├── schemas/
    │   └── trend.py              # Pydantic 응답 모델
    └── agents/
        └── aggregator/
            ├── mock_data.py      # 가상 통합 데이터 생성
            ├── prompts.py        # Gemini 시스템·유저 프롬프트
            ├── nodes.py          # Gemini 호출 + LangGraph 노드
            ├── graph.py          # (향후) LangGraph 워크플로
            ├── state.py          # (향후) 그래프 상태 스키마
            └── tool.py           # (향후) 에이전트 도구
```

> **참고:** 기존 `backend/main.py`(uv init placeholder)는 삭제되었습니다. 서버 진입점은 `app/main.py` 하나만 사용합니다.

---

## 8. 핵심 모듈 상세

### 8.1 `mock_data.py` — 가상 통합 데이터 생성

**목적:** 실제 DB·타 에이전트 연동 전까지 파이프라인을 구동할 샘플 데이터를 생성합니다.

**핵심 함수:**

```python
generate_mock_integrated_data(seed: int | None = None) -> MockIntegratedData
```

- `seed`를 지정하면 **재현 가능한** 동일 데이터가 생성됩니다 (테스트·디버깅용).
- `seed=None`이면 매 호출마다 다른 랜덤 데이터가 생성됩니다.

**8각 성향 점수 생성 로직 (`_build_profile_axis_scores`):**

- 코호트 내 **우세 축 1~2개** → 높은 점수 (68~92)
- **저조 축 1~2개** → 낮은 점수 (18~baseline)
- 나머지 → 축별 기본 구간 내 중간 점수

단순 균등 랜덤이 아니라, 실제 통계 분포처럼 **쏠림이 있는 코호트**를 모사합니다.

---

### 8.2 `prompts.py` — Gemini 프롬프트 정의

**구성 요소:**

| 상수/함수 | 설명 |
|-----------|------|
| `REPORT_MARKDOWN_TEMPLATE` | Gemini가 반드시 따를 Markdown 리포트 양식 |
| `AGGREGATOR_SYSTEM_PROMPT` | B2B 미디어·트렌드 마켓 인텔리전스 분석가 페르소나 |
| `REPORT_USER_PROMPT_TEMPLATE` | JSON 데이터 + 분석 지시를 담은 유저 프롬프트 |
| `build_report_user_prompt()` | 통합 데이터를 JSON 문자열로 직렬화 |

**분석 관점:**

- 내부 유저 **8각 성향 분포** vs 외부 **시장 트렌드 키워드** 격차
- 예: 코호트가 `entertainment_release`(오락·해방)에 치우쳤는데, 외부는 `social_awareness`(사회·시선) 키워드가 상위 → 필터 버블·미디어 편향 신호로 해석
- **미디어 중립성 점수** (0~100) 자체 산출 및 근거 제시

---

### 8.3 `nodes.py` — Gemini 연동 및 LangGraph 노드

**핵심 함수:**

| 함수 | 설명 |
|------|------|
| `get_gemini_model()` | `ChatGoogleGenerativeAI` 인스턴스 반환 |
| `resolve_gemini_model()` | 모델명 결정 (기본: `gemini-2.5-flash`) |
| `generate_b2b_report()` | Mock 데이터 → Gemini → Markdown 리포트 |
| `generate_report_node()` | LangGraph용 노드 (state in/out) |

**모델 폴백 전략:**

1. 기본 모델 `gemini-2.5-flash` 호출
2. 실패 시 `gemini-1.5-flash`로 자동 재시도
3. `GEMINI_MODEL` 환경 변수로 수동 오버라이드 가능

**LangGraph 상태 (`AggregatorNodeState`):**

```python
{
    "integrated_data": MockIntegratedData,  # 입력
    "report_markdown": str,                 # 출력
}
```

향후 `graph.py`에서 이 노드를 워크플로에 연결할 예정입니다.

---

### 8.4 `schemas/trend.py` — API 응답 계약

프론트엔드와 백엔드 사이의 **타입 계약**을 Pydantic으로 정의합니다.

| 모델 | 용도 |
|------|------|
| `KeywordStatSchema` | 키워드 통계 1건 |
| `ProfileAxisSchema` | 8각 차트 축 1개 (`key`, `label`, `avg_score`) |
| `DashboardResponse` | 대시보드 API 응답 |
| `GraphViewResponse` | 8각 차트 API 응답 (axes 8개 고정) |

---

### 8.5 `api/v1/trend.py` — REST 라우터

FastAPI **의존성 주입(Depends)** 으로 Agent 호출을 분리했습니다.

```python
get_integrated_data()  → generate_mock_integrated_data()
get_b2b_report(data)   → generate_b2b_report(data)
```

동일 요청 내에서 `get_integrated_data`는 FastAPI 캐시로 **한 번만** 실행됩니다.

---

## 9. 데이터 스키마

### 9.1 통합 Mock 데이터 (`MockIntegratedData`)

```json
{
  "schema_version": "0.2.0",
  "generated_at": "2026-06-08T10:29:14.796561+00:00",
  "internal_user_stats": {
    "top_keywords": [
      {
        "keyword": "AI 에이전트",
        "frequency": 8364,
        "trend_delta_pct": -2.7
      }
    ],
    "cognitive_bias_map": {
      "axes": [
        {
          "key": "intellectual_curiosity",
          "label": "지적 호기심",
          "avg_score": 73.3
        }
      ],
      "cohort_size": 12450,
      "measurement_period": "2026-06-01 ~ 2026-06-08"
    }
  },
  "external_market_trends": {
    "google_trends": [
      {
        "keyword": "ChatGPT",
        "rank": 1,
        "interest_index": 87,
        "wow_change_pct": 12.4
      }
    ],
    "youtube_trending": [
      {
        "keyword": "넷플릭스 신작",
        "rank": 1,
        "category": "엔터테인먼트",
        "estimated_views": 3200000
      }
    ],
    "data_collected_at": "2026-06-08T10:29:14.796561+00:00"
  }
}
```

### 9.2 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `schema_version` | string | 데이터 스키마 버전 (현재 `0.2.0`) |
| `generated_at` | ISO 8601 string | 데이터 생성 시각 (UTC) |
| `top_keywords[].keyword` | string | 비식별 집계된 상위 검색·시청 키워드 |
| `top_keywords[].frequency` | int | 해당 키워드 출현 빈도 |
| `top_keywords[].trend_delta_pct` | float | 전주 대비 변화율 (%) |
| `cognitive_bias_map.axes[].key` | string | 8각 축 시스템 Key (프로파일러 공통) |
| `cognitive_bias_map.axes[].label` | string | UI 표시 라벨 |
| `cognitive_bias_map.axes[].avg_score` | float | 코호트 평균 점수 (0~100) |
| `cognitive_bias_map.cohort_size` | int | 분석 대상 유저 수 (비식별) |
| `google_trends` | array | Google Trends 상위 키워드 (Mock) |
| `youtube_trending` | array | YouTube 급상승 키워드 (Mock) |

---

## 10. 8각 인지 성향 차트 (프로파일러 공통 스키마)

Profiler 에이전트 팀과 싱크하여 확정된 **시스템 공통 8축**입니다.  
Aggregator의 `cognitive_bias_map.axes`와 프론트엔드 8각 차트 컴포넌트가 동일한 Key·라벨을 사용합니다.

| # | UI 라벨 | Key | 점수 해석 |
|---|---------|-----|-----------|
| 1 | 지적 호기심 | `intellectual_curiosity` | 깊은 탐구·지식 탐색 성향 |
| 2 | 자기계발 | `self_improvement` | 성장·스킬업 콘텐츠 선호 |
| 3 | 사회·시선 | `social_awareness` | 사회 이슈·여론·시사 관심 |
| 4 | 깊이·몰입 | `depth_immersion` | 장형·심층 콘텐츠 몰입 |
| 5 | 실용 지향 | `practical_orientation` | 실생활 적용·하우투 선호 |
| 6 | 정서·위로 | `emotional_comfort` | 감정적 안정·공감 콘텐츠 |
| 7 | 창의·표현 | `creative_expression` | 창작·자기표현 콘텐츠 |
| 8 | 오락·해방 | `entertainment_release` | 오락·스트레스 해소 소비 |

- 점수 범위: **0 ~ 100** (높을수록 해당 성향이 강함)
- Aggregator 분석 기준: **70+** → 쏠림 리스크, **40-** → 미개발 기회

---

## 11. Gemini 리포트 생성 파이프라인

### 리포트 Markdown 구조 (고정 템플릿)

Gemini는 아래 3단 구조를 **반드시** 따릅니다.

```markdown
# 요약
  - 핵심 인사이트, 미디어 중립성 점수, B2B 시사점

## 매크로 트렌드 TOP 5
  ### 내부 유저 상위 키워드 TOP 5
  ### 외부 시장 급상승 TOP 5
  ### 격차 하이라이트 (교집합 / 내부 우세 / 외부 우세)

## 미디어 중립성 및 성향 분포 평가
  ### 8각 인지 성향 분포 (코호트 평균)
  ### 성향-트렌드 격차 분석
  ### 미디어 중립성 종합 평가

## 부록: 데이터 출처
```

### 호출 흐름

```
generate_b2b_report(data)
    │
    ├─ SystemMessage(AGGREGATOR_SYSTEM_PROMPT)
    ├─ HumanMessage(build_report_user_prompt(data))
    │
    ▼
ChatGoogleGenerativeAI (gemini-2.5-flash, temperature=0.4)
    │
    ▼
Markdown 문자열 반환
```

---

## 12. REST API 명세

**Base URL:** `http://localhost:8000`  
**Swagger UI:** `http://localhost:8000/docs`

### `GET /health`

헬스체크.

**응답 예시:**
```json
{ "status": "ok" }
```

---

### `GET /api/v1/trend/graph`

8각 인지 성향 차트용 데이터. **Gemini 호출 없음** (빠른 응답).

**응답 스키마 (`GraphViewResponse`):**

```json
{
  "cohort_size": 14303,
  "axes": [
    {
      "key": "intellectual_curiosity",
      "label": "지적 호기심",
      "avg_score": 43.7
    },
    {
      "key": "self_improvement",
      "label": "자기계발",
      "avg_score": 52.8
    }
    // ... 총 8개 축
  ]
}
```

**프론트엔드 바인딩 예시 (의사 코드):**

```typescript
const { axes, cohort_size } = await fetch("/api/v1/trend/graph").then(r => r.json());

// Radar chart
const labels = axes.map(a => a.label);
const values = axes.map(a => a.avg_score);
```

---

### `GET /api/v1/trend/dashboard`

대시보드용 키워드 통계 + Gemini 생성 Markdown 리포트.  
**Gemini API 키 필요** (없으면 500 에러).

**응답 스키마 (`DashboardResponse`):**

```json
{
  "generated_at": "2026-06-08T10:29:14.796561+00:00",
  "top_keywords": [
    {
      "keyword": "AI 에이전트",
      "frequency": 8364,
      "trend_delta_pct": -2.7
    }
  ],
  "report_markdown": "# 요약\n\n> 리포트 메타: ..."
}
```

> **주의:** `/dashboard`와 `/graph`는 각각 독립적으로 `generate_mock_integrated_data()`를 호출하므로, **동일 시점에 호출해도 서로 다른 랜덤 데이터**가 반환될 수 있습니다. 향후 세션·캐시·DB 연동 시 일관성을 보장할 예정입니다.

---

## 13. 환경 변수 설정

`backend/.env` 파일에 아래 변수를 설정합니다. (`.gitignore` 대상, **커밋 금지**)

```env
# 필수: /api/v1/trend/dashboard 호출 시
GOOGLE_API_KEY=your_gemini_api_key_here

# 선택: GEMINI_API_KEY 도 동일하게 인식됨
# GEMINI_API_KEY=your_gemini_api_key_here

# 선택: 모델 오버라이드 (기본값: gemini-2.5-flash)
# GEMINI_MODEL=gemini-1.5-flash
```

| 변수 | 필수 | 설명 |
|------|------|------|
| `GOOGLE_API_KEY` | dashboard 호출 시 | Google Gemini API 키 |
| `GEMINI_API_KEY` | 대안 | `GOOGLE_API_KEY`와 동일 역할 |
| `GEMINI_MODEL` | 선택 | `gemini-2.5-flash` 또는 `gemini-1.5-flash` |

---

## 14. 로컬 실행 방법

### 사전 요구사항

- Python 3.12
- [uv](https://github.com/astral-sh/uv) 패키지 매니저

### 설치 및 실행

```bash
# 1. backend 디렉터리로 이동
cd backend

# 2. 의존성 설치 (최초 1회)
uv sync

# 3. 환경 변수 설정
# .env 파일에 GOOGLE_API_KEY 작성

# 4. 개발 서버 실행
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 동작 확인

```bash
# 헬스체크
curl http://localhost:8000/health

# 8각 차트 데이터 (API 키 불필요)
curl http://localhost:8000/api/v1/trend/graph

# 대시보드 + Gemini 리포트 (API 키 필요)
curl http://localhost:8000/api/v1/trend/dashboard
```

### Mock 데이터 단독 테스트

```bash
uv run python -c "
from app.agents.aggregator.mock_data import generate_mock_integrated_data
import json
print(json.dumps(generate_mock_integrated_data(seed=42), ensure_ascii=False, indent=2))
"
```

### 린트

```bash
uv run ruff check app/
```

---

## 15. 데이터 흐름 다이어그램

### API 요청 흐름 (`/dashboard`)

```
Client (Frontend)
      │
      │  GET /api/v1/trend/dashboard
      ▼
┌─────────────────┐
│ trend.py        │
│ read_trend_     │
│ dashboard()     │
└────────┬────────┘
         │ Depends
         ├──────────────────────────────────┐
         ▼                                  ▼
┌─────────────────┐              ┌─────────────────┐
│ mock_data.py    │              │ nodes.py        │
│ generate_mock_  │──data───────▶│ generate_b2b_   │
│ integrated_data │              │ report()        │
└─────────────────┘              └────────┬────────┘
                                          │
                                          ▼
                                 ┌─────────────────┐
                                 │ Gemini API      │
                                 │ 2.5-flash       │
                                 └────────┬────────┘
                                          │
                                          ▼
                                 ┌─────────────────┐
                                 │ DashboardResponse│
                                 │ (Pydantic)      │
                                 └─────────────────┘
```

### API 요청 흐름 (`/graph`)

```
Client → GET /api/v1/trend/graph
              │
              ▼
         mock_data.py (generate_mock_integrated_data)
              │
              ▼
         cognitive_bias_map 파싱
              │
              ▼
         GraphViewResponse (cohort_size + axes[8])
```

---

## 16. 아직 구현되지 않은 항목 (향후 작업)

| 항목 | 파일/위치 | 설명 |
|------|-----------|------|
| LangGraph 워크플로 | `agents/aggregator/graph.py` | 노드들을 그래프로 연결 |
| 그래프 상태 | `agents/aggregator/state.py` | `AggregatorNodeState` 확장 |
| 서비스 레이어 | `app/services/` | PDF 변환, 캐싱 등 결정론적 로직 |
| PDF 다운로드 API | `api/v1/` | Markdown → HTML → PDF |
| 실데이터 연동 | Profiler, Indexer 등 | Mock → 실제 DB/API |
| 데이터 일관성 | API 레이어 | dashboard/graph 동일 데이터 보장 |
| CORS 설정 | `app/main.py` | 프론트엔드(localhost:3000) 연동 |
| 프론트 대시보드 | `frontend/` | 8각 차트 + 리포트 렌더링 |

---

## 17. 프론트엔드 연동 가이드

### 권장 연동 순서

1. **`GET /api/v1/trend/graph`** 로 8각 Radar/Spider 차트 렌더링
2. **`GET /api/v1/trend/dashboard`** 로 키워드 테이블 + Markdown 리포트 표시
3. Markdown은 `react-markdown` 등으로 렌더링

### CORS (백엔드 추가 필요 시)

프론트엔드(Next.js, `localhost:3000`)에서 API를 호출하려면 `app/main.py`에 CORS 미들웨어 추가가 필요합니다.

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 프론트엔드 에이전트 정의 (기존)

`frontend/lib/agents.ts`에 Aggregator가 이미 등록되어 있습니다.

```typescript
{
  id: "aggregator",
  name: "Aggregator",
  description: "수많은 디지털 자아들을 모아 트렌드를 읽어내는 시장 분석가",
}
```

향후 `frontend/app/agents/aggregator/` 또는 대시보드 페이지에서 위 API를 호출하면 됩니다.

---

## 부록: 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-06-08 | Aggregator MVP 초기 구현 (mock_data, prompts, nodes) |
| 2026-06-08 | 프로파일러 8각 축 스키마 반영 (v0.2.0) |
| 2026-06-08 | REST API 엔드포인트 추가 (dashboard, graph) |
| 2026-06-08 | `app/main.py` FastAPI 앱 구성, `backend/main.py` 삭제 |

---

*문서 관련 문의는 Aggregator 에이전트 담당자 또는 백엔드 팀에 연락해 주세요.*
