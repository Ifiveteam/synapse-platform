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
| `backend/app/agents/archiver/` | LangGraph 엔진 (`engine.py`, `workflow.py`, `steps/`, `nodes/`) |
| `backend/app/services/archiver_service.py` | I/O·multi-turn·SSE |
| `backend/app/repositories/archiver_repository.py` | DB·hybrid RAG |
| `extension/src/features/chat/` | 사이드패널 채팅 UI (`useChat` → `useArchiver` 위임) |
| `extension/src/features/archiver/` | 엔진·탭 컨텍스트·DOM 추출 (`useArchiver`, `services/archiverClient.ts`) |
| `extension/src/features/archiver/services/archiverClient.ts` | REST (sessions, history) + SSE 스트림 구독·파싱 SSOT |
| `extension/src/features/archiver/services/queryTabContext.ts` | 활성 탭 TabContext 조회 (1차 meta / 2차 DOM) |
| `shared/archiver-context.ts` | TabContext TypeScript SSOT (OpenAPI codegen) |

## Scrap 탭 (Archiver와 분리)

사이드패널 **Scrap** 탭은 UI를 유지하되, **Archiver 백엔드·RAG와는 연결되지 않는다.**

| 항목 | Scrap 탭 | Archiver (채팅 탭) |
|------|----------|-------------------|
| 저장소 | `chrome.storage.local` (`synapse_scrap_list`) | PostgreSQL `ai_chat_logs` + hybrid RAG |
| 인증 | 없음 (AuthGate 밖) | Bearer JWT 필수 |
| 쓰기 경로 | **미구현** — 목록 읽기·삭제만 (`useScrap`) | 채팅 스트림·세션 API |
| FAB 스크랩 버튼 | 스텁 (`FloatingWidget.handleScrapPage` → storage 미기록) | Archiver `tabContext` / DOM 브릿지와 무관 |

**로컬 스키마** (`extension/src/features/scrap/hooks/useScrap.ts`):

```ts
{ id: string; url: string; title: string; scrapedAt: string }
```

**소스:** `extension/src/features/scrap/` (`ScrapView`, `ScrapCard`, `useScrap`), 탭 전환은 `sidepanel/components/SidepanelLayout.tsx`.

**스크랩 → AI RAG 연동:** 미정(나중에 논의). 예: FAB에서 local 저장만 할지, `past_knowledge` / 별 API로 서버 동기화할지는 제품 기획 후 별도 티켓.

웹 앱 `frontend/`의 Scrap 페이지는 mock 데이터이며 익스텐션 storage와 동기화하지 않는다.

## 로컬 실행

```powershell
# DB 마이그레이션
cd backend
uv run alembic upgrade head

# API
uv run uvicorn app.main:app --reload

# 테스트
$env:PYTHONPATH="."
uv run python scripts/archiver/run_archiver_tests.py
```

**환경 변수:** `GOOGLE_API_KEY` 또는 `GEMINI_API_KEY` (Gemini), `OPENAI_API_KEY` (RAG 벡터 검색, 없으면 키워드만).
