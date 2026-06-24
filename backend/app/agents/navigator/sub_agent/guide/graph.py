"""가이드 서브에이전트 그래프 — retrieve→generate→evaluate (⇄ retrieve/generate) → END."""

from __future__ import annotations

import uuid
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.navigator.ideal import compare, extract_8axis
from app.agents.navigator.schemas import Guide, RadarComparison
from app.agents.navigator.sub_agent.guide.constants import WEAK_AXES_TOP_K
from app.agents.navigator.sub_agent.guide.nodes import evaluate, generate, retrieve
from app.agents.navigator.sub_agent.guide.state import GuideState
from app.agents.navigator.sub_agent.guide.store import CatalogStore, build_run_config


def route_after_evaluate(
    state: GuideState,
) -> Literal["retrieve", "generate", "done"]:
    decision = state.get("decision", "done")
    if decision in ("retrieve", "generate"):
        return decision
    return "done"


_compiled = None


def build_guide_graph():
    graph = StateGraph(GuideState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_node("evaluate", evaluate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {"retrieve": "retrieve", "generate": "generate", "done": END},
    )
    return graph.compile()


def _get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_guide_graph()
    return _compiled


def _select_weak_axes(comparison: RadarComparison) -> list[str]:
    positive = [(a, g) for a, g in comparison.gap_by_axis.items() if g > 0]
    positive.sort(key=lambda x: x[1], reverse=True)
    return [axis for axis, _ in positive[:WEAK_AXES_TOP_K]]


async def run_guide(
    *,
    store: CatalogStore | None,
    user_id: uuid.UUID,
    profile_21: dict[str, float],
    ideal_8: dict[str, float],
    ideal_type: str,
    reasoning: str,
) -> Guide:
    """약한 축 선정 → 그래프(RAG·생성·자기검증 루프) 실행 → Guide."""
    comparison = compare(extract_8axis(profile_21), ideal_8)
    weak_axes = _select_weak_axes(comparison)

    if not weak_axes:
        return Guide(
            summary="현재 프로필이 이미 이상향에 가깝습니다. 지금 습관을 유지하세요.",
            steps=[],
        )

    initial: GuideState = {
        "user_id": user_id,
        "profile_21": profile_21,
        "ideal_8": ideal_8,
        "ideal_type": ideal_type,
        "reasoning": reasoning,
        "weak_axes": weak_axes,
        "gap_by_axis": comparison.gap_by_axis,
        "evidence": {},
        "retrieve_attempts": 0,
        "gen_attempts": 0,
        "relax_level": 0,
    }

    final = await _get_graph().ainvoke(initial, config=build_run_config(store))
    result = final.get("result") or final.get("draft")
    if result is None:
        return Guide(
            summary="가이드를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.",
            steps=[],
        )
    return result
