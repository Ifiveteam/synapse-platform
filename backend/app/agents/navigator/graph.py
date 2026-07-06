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
from app.agents.navigator.nodes._common import (
    latest_ai_message,
    latest_user_message,
)
from app.agents.navigator.state import NavigatorState

# 사용자가 대화를 끝내고 싶다는 신호(키워드) — 있으면 곧장 마무리
_STOP_HINTS = (
    "그만",
    "됐어",
    "됐다",
    "끝내",
    "끝낼",
    "이걸로",
    "여기까지",
    "마무리",
    "그만할",
)

# 직전 네비게이터 발화가 '마무리를 제안'했는지 판별하는 문구
# (인사말 "만들어볼게요"는 제외되도록 구체 어구만)
_FINALIZE_OFFER_HINTS = (
    "만들어도",
    "만들어가",
    "구체화",
    "확정",
    "이대로",
    "완성해",
)


def _stop_keyword(state: NavigatorState) -> bool:
    last = latest_user_message(state)
    return any(hint in last for hint in _STOP_HINTS)


def _ai_offered_finalize(state: NavigatorState) -> bool:
    """직전 AI 발화가 '이대로 만들어도 될까요?'처럼 마무리를 제안한 문맥인지."""
    last_ai = latest_ai_message(state)
    return any(hint in last_ai for hint in _FINALIZE_OFFER_HINTS)


def _sequential_turn(state: NavigatorState) -> bool:
    """확정 버튼·종료 키워드·마무리 제안 문맥이면 assess를 먼저 돌리는 순차 턴."""
    return bool(
        state.get("force_finalize")
        or _stop_keyword(state)
        or _ai_offered_finalize(state)
    )


def route_start(state: NavigatorState) -> list[str] | str:
    """마무리 가능성 있는 턴이면 assess 먼저(순차), 아니면 assess∥ask 병렬."""
    if _sequential_turn(state):
        return "assess"
    return ["assess", "ask"]


def route_after_assess(state: NavigatorState) -> str:
    """확정 버튼·키워드·LLM 판단(user_wants_finalize)이면 finalize.
    마무리 제안 문맥이었지만 LLM이 '아직 아니다'로 보면 질문(ask)으로.
    일반(병렬) 턴은 ask가 답변을 맡으므로 종료(END)."""
    if not _sequential_turn(state):
        return END
    if (
        state.get("force_finalize")
        or _stop_keyword(state)
        or state.get("user_wants_finalize")
    ):
        return "finalize"
    return "ask"


def build_navigator_graph():
    graph = StateGraph(NavigatorState)
    graph.add_node("assess", assess)
    graph.add_node("ask", ask)
    graph.add_node("finalize", finalize)
    graph.add_conditional_edges(START, route_start, ["assess", "ask"])
    graph.add_conditional_edges(
        "assess",
        route_after_assess,
        {"finalize": "finalize", "ask": "ask", END: END},
    )
    graph.add_edge("ask", END)
    graph.add_edge("finalize", END)
    return graph.compile()
