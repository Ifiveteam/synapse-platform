"""Navigator LangGraph 빌드 — 취향 인터뷰 루프.

일반 턴:  START ──▶ [assess ∥ ask] → END
  - ask(답변)를 assess(이상향 갱신, 구조화 출력) 완료를 기다리지 않고 **병렬**로
    스트리밍한다 → 사용자는 답변을 즉시 보고, 성향·도메인 차트는 assess가 끝나는
    대로 갱신된다(체감 지연 감소).
확정 턴:  START ──▶ assess ──▶ finalize → END   (force_finalize=완성 버튼)
  - finalize는 확정된 이상향(persona·reasoning)이 필요하므로 assess 뒤에 순차 실행.
루프는 요청마다 한 턴씩 도는 컨트롤러다(사용자 답변 = 새 요청).
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.navigator.nodes import ask, assess, finalize
from app.agents.navigator.nodes._common import latest_user_message
from app.agents.navigator.state import NavigatorState

# 사용자가 대화를 끝내고 싶다는 신호(키워드) — 있으면 병렬 답변 대신 finalize로 마무리
_STOP_HINTS = (
    "그만",
    "됐어",
    "됐다",
    "끝내",
    "끝낼",
    "이걸로",
    "이대로",
    "여기까지",
    "완성",
    "마무리",
    "그만할",
)


def _wants_finalize(state: NavigatorState) -> bool:
    """확정 버튼(force_finalize) 또는 '그만/됐어' 같은 종료 의도면 True."""
    if state.get("force_finalize"):
        return True
    last = latest_user_message(state)
    return any(hint in last for hint in _STOP_HINTS)


def route_start(state: NavigatorState) -> list[str] | str:
    """종료 의도면 assess→finalize 순차, 아니면 assess∥ask 병렬."""
    if _wants_finalize(state):
        return "assess"
    return ["assess", "ask"]


def route_after_assess(state: NavigatorState) -> str:
    """종료 의도 턴에서만 finalize로. 일반(병렬) 턴은 ask가 답변을 맡으므로 종료."""
    return "finalize" if _wants_finalize(state) else END


def build_navigator_graph():
    graph = StateGraph(NavigatorState)
    graph.add_node("assess", assess)
    graph.add_node("ask", ask)
    graph.add_node("finalize", finalize)
    graph.add_conditional_edges(START, route_start, ["assess", "ask"])
    graph.add_conditional_edges(
        "assess",
        route_after_assess,
        {"finalize": "finalize", END: END},
    )
    graph.add_edge("ask", END)
    graph.add_edge("finalize", END)
    return graph.compile()
