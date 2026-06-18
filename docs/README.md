# docs

플랫폼 문서를 모아 두는 폴더.

**처음 시작:** [가이드](./GUIDE.md) — 클론 후 `uv sync`, `pre-commit install`

- **루트 (`docs/`)** — 에이전트 공통 문서 (아키텍처, 용어, API 개요 등)
- **하위 폴더** — 에이전트별 문서

| 폴더 | 에이전트 |
|------|----------|
| `frontend/` | [개요](./frontend/OVERVIEW.md), [폴더 구조](./frontend/FOLDER_STRUCTURE.md) |
| `backend/` | [개요](./backend/OVERVIEW.md) — 로컬 dev: `docker compose -f docker-compose.dev.yml up` |
| `indexer/` | Indexer |
| `profile/` | Profiler — [README](./profile/README.md), [IMPLEMENTATION](./profile/IMPLEMENTATION.md), [SYNAPSE_8](./profile/SYNAPSE_8.md) |
| `navigator/` | Navigator |
| `aggregator/` | Aggregator |
| `archiver/` | Archiver — [README](./archiver/README.md), [ARCHITECTURE](./archiver/ARCHITECTURE.md) |
