# Backend 개요

FastAPI + LangGraph 멀티 에이전트 백엔드의 `backend/app/` 폴더 역할과 레이어 규칙.

- 실행: `cd backend && uv sync && uv run uvicorn app.main:app --reload`
- Docker: `docker compose up` (루트 `migrate` → `alembic upgrade head` 자동)
- **로컬 dev:** `docker compose -f docker-compose.dev.yml up` + `frontend`에서 `pnpm dev`
- 환경 변수: `backend/.env.example`, `frontend/.env.example` 참고

## 레이어 요약

```
app/
├── main.py              FastAPI HTTP 진입점
├── celery_app.py        Celery worker/beat 진입점
│
├── api/v1/              HTTP 라우터 (얇은 어댑터)
├── schemas/             Pydantic BaseModel — API 요청·응답
├── services/            에이전트 밖·사이 orchestration (job, PDF, 메일 등)
├── agents/              LangGraph 에이전트 (파이프라인·LLM·도메인)
├── models/              SQLAlchemy Base — DB 테이블 ORM
├── repositories/        Repository 패턴 (DB 접근, 현재 대부분 분산)
└── core/                설정·env·DB 세션·JWT 등 앱 공통
```

호출 방향:

```
api/v1  →  services  →  agents
              ↓
         models / repositories / core
```

- `api`는 검증·라우팅·`response_model`만 담당한다.
- `agents`는 `api`·`services`를 import하지 않는다.

## 폴더별 설명

### `core/`

앱 전역 **설정·인프라**.

| 경로 | 역할 |
|------|------|
| `env.py` | `.env` 로드 |
| `config.py` | `DATABASE_URL` 등 런타임 설정 |
| `security.py` | JWT 발급·검증 |
| `database/` | SQLAlchemy `Base`, async session, Alembic 모델 import |

### `schemas/`

**HTTP 경계**용 Pydantic `BaseModel`. FastAPI `response_model`·OpenAPI.

| 파일 | 용도 |
|------|------|
| `profiler.py` | Profiler API |
| `trend.py` | Aggregator 트렌드 API |
| `auth.py` | Auth API (`UserResponse`, `DevLoginResponse`) |
| `report.py` | 대시보드 리포트 DTO (에이전트·서비스와 공유) |

에이전트 **내부 도메인** Pydantic은 `agents/{name}/base/`(Profiler) 또는 `agents/{name}/schemas.py`(Navigator)에 둔다. `schemas/`와 역할을 구분한다.

### `models/`

SQLAlchemy **`DeclarativeBase`** — DB 테이블 ORM.

| 모델 | 테이블 |
|------|--------|
| `user.py` | `users` |
| `video_vector.py` | `video_vectors` (pgvector) |

Profiler 프로필·스냅샷 등은 현재 JSON mock 위주 — DB 미연동 항목은 에이전트별 문서 참고.

### `repositories/`

**Repository 패턴** — DB·저장소 CRUD를 캡슐화하는 레이어.

`app/repositories/`에 인덱서 repository가 이동되었고, 일부 구현은 여전히 분산되어 있다.

| 위치 | 역할 |
|------|------|
| `repositories/indexer_repository.py` | `user_watch_catalog` CRUD/집계 |
| `services/trend/repository.py` | 트렌드 게시글 인메모리 저장 |

공통 repository가 필요해지면 이 폴더에 추가한다.

### `services/`

**에이전트가 아닌** 기능, 또는 **HTTP와 agents 사이** orchestration.

| 경로 | 역할 |
|------|------|
| `profiler/` | job·스냅샷·compare·graph_view |
| `trend/` | 게시판·mapper·PDF |
| `email.py`, `notification.py` | 메일·알림 |
| `pdf.py` | Markdown → PDF |
| `external_trends.py` | 외부 트렌드 fetch |
| `takeout_service.py` | Google Takeout ZIP |

에이전트 전용 서비스(`profiler/`, `trend/`)도 있지만, **LangGraph 그래프 자체는 `agents/`**에 둔다.

### `agents/`

**에이전트 기능** — LangGraph 파이프라인, LLM, 도메인 로직.

| 에이전트 | 상태 | API |
|----------|------|-----|
| `profiler/` | 구현 | `/api/v1/profiler` |
| `aggregator/` | 구현 | `/api/v1/trend` |
| `indexer/` | 구현 | `/api/v1/indexer` |
| `navigator/` | 구현 | `/api/v1/navigator` |
| `archiver/` | 스켈레톤 | — |

#### 에이전트 공통 하위 구조 (에이전트마다 일부만 존재)

```
agents/{name}/
├── graph.py           LangGraph 그래프 정의·실행
├── state/             LangGraph 실행 상태 (TypedDict 등)
├── nodes/             그래프 노드 함수
├── base/              내부 도메인 Pydantic (Profiler)
├── schemas.py         내부 스키마 (Navigator 등)
├── prompt.py          LLM 프롬프트
├── tools.py           tool·집계 (Indexer, Profiler)
├── sub_agent/         서브 에이전트 (Aggregator)
├── repository.py      DB 접근 (Indexer)
├── scheduler.py       Celery 태스크 (Indexer)
└── scripts/           mock·CLI (Profiler)
```

**`state/`** — 그래프 실행 중 흘러가는 **변수·중간 결과**만 정의한다. API DTO·ORM 타입을 넣지 않는다. `base/` 타입을 필드로 참조하는 패턴(Profiler)을 따른다.

**`nodes/`** — `state`를 읽고 갱신하는 **단계별 처리** (load, LLM, notify 등).

**`graph.py`** — `nodes`와 `state`를 묶어 `StateGraph`를 구성하고 `run_*` 진입점을 제공한다.

에이전트별 상세:

- Profiler — [docs/profile/PIPELINE.md](../profile/PIPELINE.md)
- Aggregator — [docs/aggregator/ARCHITECTURE.md](../aggregator/ARCHITECTURE.md)

### `api/v1/`

FastAPI **HTTP 진입점**. 라우터만 얇게 유지한다.

| 파일 | 대상 |
|------|------|
| `auth.py` | OAuth·JWT |
| `profiler.py` | Profiler |
| `trend.py` | Aggregator 트렌드 |
| `indexer.py` | Indexer |
| `navigator.py` | Navigator |
| `takeout.py` | Takeout 업로드 |

`__init__.py`에서 `api_router`로 `/api/v1`에 마운트.

### `main.py` · `celery_app.py`

| 파일 | 프로세스 |
|------|----------|
| `main.py` | FastAPI 앱 (`uvicorn app.main:app`) |
| `celery_app.py` | Celery worker/beat (`celery -A app.celery_app`). Redis broker, Indexer 주간 가중치 스케줄 |

## `backend/` 루트 (app 밖)

| 경로 | 역할 |
|------|------|
| `alembic/` | DB 마이그레이션 (`alembic upgrade head`) |
| `pyproject.toml` | Python 의존성·Ruff |
| `.env.example` | 로컬 시크릿 템플릿 |

## 타입·스키마 배치 규칙

| 종류 | 위치 |
|------|------|
| API 요청·응답 | `schemas/` |
| 에이전트 내부 도메인 | `agents/{name}/base/` 또는 `agents/{name}/schemas.py` |
| LangGraph 실행 상태 | `agents/{name}/state/` |
| DB 테이블 | `models/` |

## 새 코드 넣을 때

| 추가하는 것 | 넣을 위치 |
|-------------|-----------|
| 새 HTTP 엔드포인트 | `api/v1/` + `schemas/` |
| LangGraph 노드·그래프 | `agents/{name}/nodes/`, `graph.py` |
| 그래프 상태 필드 | `agents/{name}/state/` |
| DB CRUD | `repositories/` 또는 `agents/.../repository.py` |
| job·PDF·메일 등 | `services/` |
| DB 테이블 | `models/` + `alembic/versions/` |
| 주기 백그라운드 작업 | `agents/.../scheduler.py` + `celery_app.py` 등록 |

## 관련 문서

| 문서 | 내용 |
|------|------|
| [profile/PIPELINE.md](../profile/PIPELINE.md) | Profiler 파이프라인·그래프·API |
| [aggregator/ARCHITECTURE.md](../aggregator/ARCHITECTURE.md) | Aggregator LangGraph·레이어 |
| `backend/app/core/README.md` 등 | 폴더별 한 줄 정의 |
