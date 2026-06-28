# Profiler

YouTube 시청 catalog를 바탕으로 **영상 의미 분석 → 21축 성향 프로필 → 완료 알림**까지 수행하는 에이전트.

## 문서

| 문서 | 내용 |
|------|------|
| [PIPELINE.md](./PIPELINE.md) | 전체 파이프라인, LangGraph, DB, API, 비동기 실행 |

## 빠른 참조

| 구분 | 경로 |
|------|------|
| 메인 LangGraph | `backend/app/agents/profiler/graph.py` |
| 영상 분석 서브그래프 | `backend/app/agents/profiler/sub_agent/video_summary/` |
| HTTP API | `backend/app/api/v1/profiler.py` |
| Job 오케스트레이션 | `backend/app/services/profiler/service.py` |
| DB 접근 | `backend/app/repositories/profiler_repository.py` |
| 영상 선별 로직 | `backend/app/services/profiler/sampling.py` |
| 공통 임베딩 | `backend/app/agents/shared/embedding.py` |
| API·LLM 스키마 | `backend/app/schemas/profiler/` |
| ERD | [docs/erd.md](../erd.md) — `video_analysis`, `user_profile_history` |

## API (프로덕션)

```text
POST /api/v1/profiler/run                    → job 시작 (202)
GET  /api/v1/profiler/jobs/{job_id}          → job 상태·결과
GET  /api/v1/profiler/me/profile             → 최신 스냅샷 조회
GET  /api/v1/profiler/me/analyses            → 분석 목록 (스냅샷 + 진행 job)
GET  /api/v1/profiler/me/analyses/compare    → 두 스냅샷 비교
GET  /api/v1/profiler/me/analyses/{id}       → 스냅샷 단건
POST /api/v1/profiler/video-summary/run      → 영상 분석만 단독 실행 (202)
```

인덱서 성공 시 `profiler_service.enqueue_for_user()`로 메인 파이프라인이 자동 큐잉된다.  
상세 흐름은 [PIPELINE.md](./PIPELINE.md) 참고.
