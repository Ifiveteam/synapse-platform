# docs

플랫폼 문서를 모아 두는 폴더.

**처음 시작:** [루트 `CLAUDE.md`](../CLAUDE.md) — 사전 요구사항, 최초 설정(`uv sync`, `pre-commit install`), 로컬 실행

- **루트 (`docs/`)** — 에이전트 공통 문서 (아키텍처, 용어, API 개요 등)
- **하위 폴더** — 에이전트별 문서

| 폴더 | 에이전트 |
|------|----------|
| `frontend/` | [개요](./frontend/OVERVIEW.md), [폴더 구조](./frontend/FOLDER_STRUCTURE.md) |
| `backend/` | [개요](./backend/OVERVIEW.md) — 로컬 dev: `docker compose -f docker-compose.dev.yml up` |
| `indexer/` | Indexer — [README](./indexer/README.md), [ARCHITECTURE](./indexer/ARCHITECTURE.md), [PIPELINE](./indexer/PIPELINE.md), [DATA](./indexer/DATA.md), [API](./indexer/API.md), [IMPLEMENTATION](./indexer/IMPLEMENTATION.md) |
| `profile/` | Profiler — [README](./profile/README.md), [PIPELINE](./profile/PIPELINE.md) |
| `navigator/` | Navigator |
| `aggregator/` | Aggregator |
| `archiver/` | Archiver — [README](./archiver/README.md), [ARCHITECTURE](./archiver/ARCHITECTURE.md) |
