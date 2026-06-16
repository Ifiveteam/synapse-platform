# repositories

DB·외부 저장소 접근 로직을 모아 두는 폴더.

인덱서 repository는 이 폴더로 이동했고, 일부 구현은 여전히 분산되어 있다.

| 위치 | 역할 |
|------|------|
| `app/repositories/indexer_repository.py` | `user_video_watch`, `user_feature_snapshot` CRUD/집계 |
| `app/services/trend/repository.py` | 트렌드 게시글 인메모리 저장 |

공통 repository가 필요해지면 이 폴더에 추가한다.
