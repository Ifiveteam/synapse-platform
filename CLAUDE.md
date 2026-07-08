# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code(및 기여자)를 위한 운영 가이드입니다.
실행 명령은 각 앱의 `package.json`/`pyproject.toml`과 `docs/`에 있으니, 여기서는 **저장소 구조와 작업 규칙·관례**에 집중합니다.

## 프로젝트 개요

Synapse — 트렌드/이상향 기반 분석 플랫폼. 하나의 모노레포에 3개의 앱이 들어 있습니다.

- **backend/** — FastAPI 기반 API + LangGraph 에이전트 파이프라인 (Python 3.12)
- **frontend/** — Vite + React 19 웹 앱 (shadcn/ui)
- **extension/** — CRXJS 기반 브라우저 확장 (React 19)

## 저장소 구조

| 경로 | 설명 |
|---|---|
| `backend/` | FastAPI 앱, 에이전트, Alembic 마이그레이션 (패키지 매니저: **uv**) |
| `frontend/` | 웹 프론트엔드 (패키지 매니저: **pnpm**) |
| `extension/` | 브라우저 확장 (패키지 매니저: **pnpm**) |
| `shared/` | 프론트↔익스텐션 공유 타입 (`auth-protocol.ts`) |
| `docs/` | 영역별 상세 문서 (`erd.md`, `backend/`, `frontend/`, 에이전트별) |
| `nginx/`, `docker-compose*.yml` | 배포/로컬 인프라 |

## 사전 요구사항

- **Git**
- **uv** (Python 3.12) — backend 의존성/실행
- **Node.js + pnpm** — frontend / extension (npm 사용 안 함)
- **Docker + Docker Compose** — 로컬 DB(pgvector) + 백엔드 구동

## ⚠️ 패키지 매니저 (가장 중요)

- **backend = `uv`**, **frontend·extension = `pnpm`**.
- **`npm`은 사용하지 않습니다.** 절대 `npm install`/`package-lock.json`을 만들지 마세요.
- 매니저를 영역끼리 섞지 마세요.

## Backend 구조 & 관례

- **레이어**: `app/api`(라우터) → `app/services`(비즈니스) → `app/repositories`(DB 접근) · `app/models`(SQLAlchemy) · `app/schemas`(Pydantic) · `app/core`(설정/DB/env).
- **에이전트** (`app/agents/`): `aggregator`, `archiver`, `curator`, `indexer`, `navigator`, `profiler`, `shared`. LangChain/LangGraph + Gemini/OpenAI 기반.
- **DB**: PostgreSQL + `pgvector`, 비동기 SQLAlchemy(asyncpg). 마이그레이션은 Alembic.
  - 모델을 바꾸면 **반드시 `backend/alembic/versions/0NN_*.py`를 추가**하고 `down_revision`을 직전 head로 지정하세요. (현재 head: `019_playlist_last_refreshed_at`)
  - `backend/scripts/reset_db.py`는 스키마를 통째로 DROP하는 **파괴적 개발용** 스크립트입니다. 운영에서 쓰지 마세요.
- **개발용 스크립트는 `backend/scripts/`에 둡니다.** 일회성 유틸·스모크 테스트·DB 리셋 등은 `app/` 안이 아니라 `scripts/`에 두세요 (예: `reset_db.py`, `archiver_*.py`).
- **Ruff** (`pyproject.toml`): line-length 88, double-quote, import 정렬(I), `E501`(라인 길이)는 한글 문자열 때문에 무시. 커밋 전 ruff 통과 필수.

## Frontend 구조 & 관례

- **UI: shadcn/ui** (style `new-york`). 새 컴포넌트는 `npx shadcn@latest add <name>` → `src/components/ui/`에 생성. 클래스 병합은 `cn()`(`@/lib/utils`). import alias는 `@/`.
- **상태관리: zustand** (`src/stores/*`). 영속화는 `persist` 미들웨어 패턴 사용.
- **API 레이어**: `src/api/*`. 스타일: Tailwind v4 (CSS 변수, `src/styles/globals.css`).

## Extension 메모

- CRXJS + Vite, 진입 설정은 `extension/manifest.ts`.
- 웹과의 인증 연동 규약은 `shared/auth-protocol.ts`를 공유합니다.

## 컨벤션 / 주의사항

- 코드·주석에 **한국어 혼용**이 일반적입니다.
- PR 전 각 앱에서 `build`(프론트/익스텐션) 또는 ruff(백엔드)를 돌려 타입/린트를 통과시키세요 — `build`가 곧 타입체크입니다.
- 커밋은 pre-commit 훅 통과가 전제입니다.
- CI(`.github/workflows/ci.yml`)는 backend 임포트 검증 + 빌드 검증, CD는 Docker Hub→EC2 배포.

## 더 보기

- 실행/명령: 각 앱 `package.json` 스크립트, `backend/pyproject.toml`(uv·ruff), 로컬 인프라 `docker-compose.dev.yml`
- 전체 문서 인덱스: `docs/README.md`
- ERD: `docs/erd.md`
- 영역별: `docs/backend/`, `docs/frontend/`, 에이전트별 `docs/<agent>/`
