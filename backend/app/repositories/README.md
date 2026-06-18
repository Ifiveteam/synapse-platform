# repositories

DB·외부 저장소 접근 로직을 모아 두는 폴더. 에이전트·API·서비스는 여기만 통해 DB에 접근합니다.

| 파일 | 테이블 / 역할 |
|------|----------------|
| `indexer_repository.py` | `user_watch_catalog` CRUD·집계 (인덱서) |
| `profiler_repository.py` | `video_analysis` upsert·조회, `user_profile_history`, catalog 읽기 (프로파일러) |
| `services/profiler/sampling.py` | 영상 분석 샘플 선정 (catalog 행 기반) |

| 기타 | |
|------|--|
| `app/services/trend/repository.py` | 트렌드 게시글 인메모리 저장 |

공통 repository가 필요해지면 이 폴더에 추가합니다.
