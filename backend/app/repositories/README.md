# repositories

DB·외부 저장소 접근 로직을 모아 두는 폴더.

현재 이 폴더는 비어 있고, 에이전트·서비스별로 repository가 분산되어 있다.

| 위치 | 역할 |
|------|------|
| `app/agents/indexer/repository.py` | `VideoVector` CRUD, 중복 검사 |
| `app/services/trend/repository.py` | 트렌드 게시글 인메모리 저장 |

공통 repository가 필요해지면 이 폴더에 추가한다.
