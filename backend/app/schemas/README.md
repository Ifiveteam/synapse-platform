# schemas

도메인별 Pydantic `BaseModel` SSOT.

| 경로 | 용도 |
|------|------|
| `schemas/profiler/api.py` | Profiler HTTP 요청·응답 |
| `schemas/profiler/profile.py` | 프로필 LLM 출력 · DB `user_profile_history` 필드명 |
| `schemas/profiler/video.py` | 영상 의미분석 LLM 출력 |
| `schemas/profiler/job.py` | 프로파일러 job 상태 enum |
| `schemas/auth.py` | 인증 API |
| `schemas/trend.py` | 트렌드 API |
| `schemas/report.py` | 리포트 (aggregator·PDF 공유) |

LangGraph `TypedDict` state는 `agents/.../state/`에 둡니다. SQLAlchemy는 `app/models/`.
