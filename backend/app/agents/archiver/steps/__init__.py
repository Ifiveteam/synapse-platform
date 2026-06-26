"""Archiver LangGraph **제어 스텝** — router / evaluator / respond / need_dom.

`workflow.py`가 이 패키지에서 가져오는 노드는 **오케스트레이션·판단·응답** 역할만 담당한다.

| 스텝        | 그래프 노드명 | 책임 |
|-------------|---------------|------|
| classify    | router        | LLM 라우터 — target_engines·route·is_general 결정 |
| evaluate    | evaluator     | 수집 근거 통합 채점 — fan-in 후 분기 |
| respond     | respond       | 최종 답변 스트리밍 |
| need_dom    | need_dom      | 클라이언트 DOM 수집 SSE 신호 · 1차 스트림 종료 |

병렬 **데이터 수집** fan-out 엔진은 `nodes/` 패키지가 담당한다 (`collect_node`, `rag_node`, `search_node`).
수집 I/O 헬퍼(스크래핑 등)는 `nodes/utils/`에 둔다.
"""

from app.agents.archiver.steps.classify import classify
from app.agents.archiver.steps.evaluate import evaluate
from app.agents.archiver.steps.need_dom import need_dom
from app.agents.archiver.steps.respond import respond

__all__ = [
    "classify",
    "evaluate",
    "need_dom",
    "respond",
]
