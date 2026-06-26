"""Archiver LangGraph **수집 엔진 노드** — router fan-out 병렬 트랙.

`workflow.py`가 이 패키지에서 가져오는 노드는 **State에 근거 데이터를 채우는** 역할만 담당한다.

| 노드          | State 필드              | 데이터 원천 |
|---------------|-------------------------|-------------|
| collect_node  | context_dom             | 클라이언트 DOM / 서버 스크래핑 |
| rag_node      | context_rag             | ArchiverStore → DB 과거 기억 |
| search_node   | context_search          | Gemini + Google Search Tool |

**`past_knowledge/` 패키지와의 경계**
- `nodes/rag.py` (`rag_node`): LangGraph 런타임 노드 — `ArchiverStore` Port로 검색을 위임한다.
- `past_knowledge/` (embedding·retrieval): 영속화·임베딩·SQL 하이브리드 검색 전략 — Repository/Store 구현체가 사용한다.
  노드가 `past_knowledge/`를 직접 import하지 않는 것이 의도된 계층 분리다.

**`nodes/utils/`**
- 스크래핑·클라이언트 본문 정규화 등 수집 I/O 헬퍼 (`scraper.py`). LangGraph 노드가 아니다.
"""

from app.agents.archiver.nodes.collect import collect_node
from app.agents.archiver.nodes.rag import rag_node
from app.agents.archiver.nodes.search import search_node

__all__ = [
    "collect_node",
    "rag_node",
    "search_node",
]

