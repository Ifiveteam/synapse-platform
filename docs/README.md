# docs

플랫폼 문서를 모아 두는 폴더.

**처음 시작:** [루트 `CLAUDE.md`](../CLAUDE.md) — 사전 요구사항, 최초 설정(`uv sync`, `pre-commit install`), 로컬 실행

- **루트 (`docs/`)** — 에이전트 공통 문서 (아키텍처, 용어, API 개요 등)
- **하위 폴더** — 에이전트별 문서

| 폴더 | 에이전트 |
|------|----------|
| `frontend/` | [README](./frontend/README.md) — 라우트·폴더 구조·배치 규칙 |
| `backend/` | [개요](./backend/OVERVIEW.md) — 로컬 dev: `docker compose -f docker-compose.dev.yml up` |
| `indexer/` | Indexer — [README](./indexer/README.md) (파이프라인·데이터·API 통합) |
| `profile/` | Profiler — [README](./profile/README.md) (파이프라인·portrait·API 통합) |
| `navigator/` | Navigator — [README](./navigator/README.md) (설계·그래프·재생목록 통합) |
| `aggregator/` | Aggregator |
| `archiver/` | Archiver — [README](./archiver/README.md), [ARCHITECTURE](./archiver/ARCHITECTURE.md) |
| `curator/` | Curator — [README](./curator/README.md) |
