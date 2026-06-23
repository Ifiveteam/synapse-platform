# Archiver 에이전트

사용자 지식 아카이빙·웹 컨텍스트 기반 Q&A LangGraph 에이전트. 익스텐션 사이드패널 채팅 UI와 연동된다.

## 문서

| 문서 | 설명 |
|------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 레이어·워크플로우·SSE·RAG·인증·테스트 |

## API (`/api/v1/archiver`)

인증: Bearer JWT (`get_current_user_dep`) 필수.

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/stream` | SSE 스트리밍 (`ChatStreamRequest`) |
| `GET` | `/sessions` | 본인 아카이버 세션 목록 |
| `GET` | `/history/{session_id}` | 세션 대화 타임라인 |

## 소스 위치

| 경로 | 역할 |
|------|------|
| `backend/app/agents/archiver/` | LangGraph 엔진·스텝 |
| `backend/app/services/archiver_service.py` | I/O·multi-turn·SSE |
| `backend/app/repositories/archiver_repository.py` | DB·hybrid RAG |
| `extension/src/features/chat/` | 사이드패널 UI |
| `extension/src/shared/api/archiverStream.ts` | SSE 파서 |

## 로컬 실행

```powershell
# DB 마이그레이션
cd backend
uv run alembic upgrade head

# API
uv run uvicorn app.main:app --reload

# 테스트
$env:PYTHONPATH="."
uv run python scripts/run_archiver_tests.py
```

**환경 변수:** `GOOGLE_API_KEY` 또는 `GEMINI_API_KEY` (Gemini), `OPENAI_API_KEY` (RAG 벡터 검색, 없으면 키워드만).
