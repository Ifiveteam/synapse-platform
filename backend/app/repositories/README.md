# repositories

DB·외부 저장소 접근 로직을 모아 두는 폴더. 에이전트·API·서비스는 여기만 통해 DB에 접근합니다.

| 파일 | 역할 |
|------|------|
| `archiver_repository.py` | Archiver 대화 로그 CRUD, RAG SQL 실행 (`ArchiverStore` 구현) |

RAG 하이브리드 검색 **전략**은 `app/agents/archiver/rag_retrieval.py`, 임베딩 생성은 `rag_embedding.py`에 둡니다.

## ArchiverRepository

`app/agents/archiver/store.ArchiverStore` Protocol을 구현해 LangGraph `collect` 스텝에 RAG Port로 주입된다.

| 메서드 | 반환 | 설명 |
|--------|------|------|
| `resolve_session_id` | `str` | 동일 `user_id`+URL 세션 재사용 또는 UUID 발급 |
| `save_chat_log` | `AIChatLog` | `ai_chat_logs` INSERT + `content_embedding` (OpenAI, optional) |
| `get_user_sessions` | `list[ArchiverSessionSummary]` | 세션 목록 (최근 활동순) |
| `get_chat_history` | `list[ArchiverChatMessage]` | 세션 대화 타임라인 (`user_id` 필터 가능) |
| `search_past_knowledge` | `list[PastKnowledgeHit]` | hybrid RAG (키워드 / pgvector / relaxed) |

### RAG 검색 전략 (`search_past_knowledge`)

전략 orchestration은 `app/agents/archiver/rag_retrieval.py`. Repository는 SQL 실행(`search_logs_by_keywords`, `search_logs_by_vector`)만 담당한다.

`retrieval_attempt` 인자로 collect 역주행 시도에 맞춰 전략이 바뀐다.

| `retrieval_attempt` | 동작 |
|---------------------|------|
| `1` | 키워드 ILIKE (토큰 추출, 최대 5개) |
| `2+` | pgvector cosine 유사도 → 결과 없으면 relaxed 전체 쿼리 ILIKE |

임베딩은 `save_chat_log` 시 `[context_title]\ncontent`로 생성한다. `OPENAI_API_KEY`가 없으면 `content_embedding`은 `NULL`이며 벡터 검색은 skip된다.

### DB 스키마 (`ai_chat_logs`)

| 마이그레이션 | 내용 |
|--------------|------|
| `005_create_ai_chat_logs` | 테이블 생성, `user_id UUID → users.id` FK, `content_embedding vector(1536)` + HNSW 인덱스 (`app.core.constants.RAG_EMBEDDING_DIM`) |

PK `id`는 Integer autoincrement (append-only 로그). `user_id`만 UUID FK.

### 상수

`ARCHIVER_AGENT_TYPE`은 `app/agents/archiver/constants.py` SSOT — repository는 import만 한다.

### Import 경계

| From → To | 허용 |
|-----------|------|
| `repositories/` → `agents/archiver/store`, `constants`, `rag_embedding`, `rag_retrieval` | ✅ |
| `repositories/` → `models/`, `schemas/` | ✅ |
| `agents/archiver/` → `repositories/` | ❌ (Service가 중개) |

## 기타 repository (분산)

| 기타 | |
|------|--|
| `app/services/trend/repository.py` | 트렌드 게시글 인메모리 저장 |
| `app/repositories/indexer_repository.py` | Indexer catalog |
| `app/repositories/profiler_repository.py` | Profiler video analysis |

공통 repository가 필요해지면 이 폴더에 추가합니다.
