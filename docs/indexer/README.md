# Indexer

Google Takeout YouTube 시청 기록을 **`user_watch_catalog`**에, 구독정보를 **`user_subscription`**에 적재하는 에이전트.
(YouTube Music 시청은 `platform=youtube_music`로 라벨)

## 문서

| 문서 | 내용 |
|------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 레이어, Drive 시퀀스, Profiler 경계, 코드 위치 |
| [PIPELINE.md](./PIPELINE.md) | S1~S5 catalog pipeline 단계별 |
| [DATA.md](./DATA.md) | catalog 필드, Takeout/API 매핑, 숏츠·썸네일 |
| [API.md](./API.md) | Takeout · Indexer HTTP API |
| [IMPLEMENTATION.md](./IMPLEMENTATION.md) | 구현 계획 · Phase · 체크리스트 |

전체 DB: [../erd.md](../erd.md)

## 빠른 참조

| 구분 | 경로 |
|------|------|
| LangGraph | `backend/app/agents/indexer/` (preprocess·diff·enrich·embed·store·subscriptions) |
| Repository | `backend/app/repositories/indexer_repository.py` |
| ORM | `backend/app/models/user_watch_catalog.py`, `user_subscription.py` |
| Takeout API | `backend/app/api/v1/takeout.py` |
| Indexer API | `backend/app/api/v1/indexer.py` |
| Drive UI | `frontend/src/components/upload/upload-panel.tsx` |

## Drive MVP 흐름

```text
GET /takeout/drive/discover → POST /trigger/{file_id} → GET /status/{task_id}
```
