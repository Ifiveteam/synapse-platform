# repositories

DB·외부 저장소 접근 로직을 모아 두는 폴더.

| 파일 | 역할 |
|------|------|
| `archiver_repository.py` | Archiver 대화 로그 CRUD, RAG 키워드 검색 (`ArchiverStore` 구현) |

## ArchiverRepository

`app/agents/archiver/store.ArchiverStore` Protocol을 구현해 LangGraph `collect` 스텝에 RAG Port로 주입된다.

| 메서드 | 반환 | 설명 |
|--------|------|------|
| `resolve_session_id` | `str` | 동일 user+URL 세션 재사용 또는 UUID 발급 |
| `save_chat_log` | `AIChatLog` | `ai_chat_logs` INSERT (`agent_type=ARCHIVER`) |
| `get_user_sessions` | `list[ArchiverSessionSummary]` | 세션 목록 (최근 활동순) |
| `get_chat_history` | `list[ArchiverChatMessage]` | 세션 대화 타임라인 |
| `search_past_knowledge` | `list[PastKnowledgeHit]` | 키워드 ILIKE RAG 검색 |

### 상수

`ARCHIVER_AGENT_TYPE`은 `app/agents/archiver/constants.py` SSOT — repository는 import만 한다.

### Import 경계

| From → To | 허용 |
|-----------|------|
| `repositories/` → `agents/archiver/store`, `constants` | ✅ |
| `repositories/` → `models/`, `schemas/` | ✅ |
| `agents/archiver/` → `repositories/` | ❌ (Service가 중개) |

## 기타 repository (분산)

| 위치 | 역할 |
|------|------|
| `app/agents/indexer/repository.py` | `VideoVector` CRUD, 중복 검사 |
| `app/services/trend/repository.py` | 트렌드 게시글 인메모리 저장 |

공통 repository가 필요해지면 이 폴더에 추가한다.
