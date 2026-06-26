# Archiver 테스트 스크립트

pytest 없이 Archiver 전용 스크립트 테스트. Mock LLM으로 실제 Gemini 호출 없이 실행 가능.

## 일괄 실행

```powershell
cd backend
$env:PYTHONPATH="."
uv run python scripts/archiver/run_archiver_tests.py
```

## 개별 실행

```powershell
$env:PYTHONPATH="."
uv run python scripts/archiver/archiver_test_unit.py
uv run python scripts/archiver/archiver_test_service.py
uv run python scripts/archiver/archiver_smoke.py
uv run python scripts/archiver/archiver_test_p2.py
uv run python scripts/archiver/archiver_test_scenarios.py
```

## 스크립트

| 파일 | 범위 |
|------|------|
| `run_archiver_tests.py` | 위 전체 러너 (진입점) |
| `archiver_test_unit.py` | branches, route 파싱, Evaluation fallback, context 유틸 |
| `archiver_test_service.py` | SSE token 격리, `should_persist_assistant_log` |
| `archiver_smoke.py` | Mock LLM 4경로 (GENERAL/RAG/SEARCH/BASIC) + evaluator |
| `archiver_test_p2.py` | SSE envelope, multi-turn history, respond tool binding |
| `archiver_test_scenarios.py` | 리팩터 회귀 시나리오 (인사·need_dom·병렬 synthesis·멀티턴) |

상세: [docs/archiver/ARCHITECTURE.md](../../../docs/archiver/ARCHITECTURE.md) §11
