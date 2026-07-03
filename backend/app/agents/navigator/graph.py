"""Navigator LangGraph 빌드 — 취향 인터뷰 루프.

START → assess ──(decision)──▶ ask → END      (질문을 던지고 다음 유저 턴 대기)
                          └──▶ finalize → END  (충분/종료 → 이상향 완성)
루프는 요청마다 한 턴씩 도는 컨트롤러다(사용자 답변 = 새 요청).
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.navigator.nodes import ask, assess, finalize
from app.agents.navigator.state import NavigatorState


def route_after_assess(state: NavigatorState) -> Literal["ask", "finalize"]:
    return "finalize" if state.get("decision") == "finalize" else "ask"


def build_navigator_graph():
    graph = StateGraph(NavigatorState)
    graph.add_node("assess", assess)
    graph.add_node("ask", ask)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "assess")
    graph.add_conditional_edges(
        "assess",
        route_after_assess,
        {"ask": "ask", "finalize": "finalize"},
    )
    graph.add_edge("ask", END)
    graph.add_edge("finalize", END)
    return graph.compile()
