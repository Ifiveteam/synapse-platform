# Profiler

YouTube 시청·검색 기록으로 **Synapse 8 Layer A + Layer B** 프로필을 산출하는 에이전트.

## 문서

| 문서 | 내용 |
|------|------|
| [IMPLEMENTATION.md](./IMPLEMENTATION.md) | 레이어 구조, 디렉터리, Import 규칙, API·데이터 흐름 |
| [SYNAPSE_8.md](./SYNAPSE_8.md) | 8축·Layer B 도메인 스펙 (측정 정의) |

## 빠른 참조

| 구분 | 경로 |
|------|------|
| LangGraph 파이프라인 | `backend/app/agents/profiler/` |
| HTTP API | `backend/app/api/v1/profiler.py` |
| Profiler 서비스 | `backend/app/services/profiler/` |
| API 스키마 | `backend/app/schemas/profiler.py` |
| Mock·CLI | `backend/app/agents/profiler/scripts/` |

## 시연 본선

```text
GET /personas → POST /analyze → GET /jobs/{id} → GET /profile/{user_id}
```

로컬 테스트: `backend/`에서 `uv run python -m app.agents.profiler.scripts.run_test mock_jiyeon`
