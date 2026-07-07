"""가이드 서브에이전트 그래프 — retrieve→generate→evaluate (⇄) → END.

심화(성향 갭, 시청 근거)와 확장(새 도메인, 다리) 두 갈래 스텝을 함께 만든다.
"""

from __future__ import annotations

import uuid
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.navigator.constants import DISPOSITION_AXES, INTEREST_DOMAINS
from app.agents.navigator.schemas import Guide
from app.agents.navigator.sub_agent.guide.constants import (
    DEEPEN_TOP_K,
    EXPAND_TOP_K,
)
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


def _positive_gaps(
    keys: tuple[str, ...],
    current: dict[str, float],
    target: dict[str, float],
    top_k: int,
) -> tuple[list[str], dict[str, float]]:
    """target > current인 축을 갭 큰 순 top_k. (타깃 리스트, 전체 갭 dict)."""
    gaps = {
        k: round(float(target.get(k, 0.0)) - float(current.get(k, 0.0)), 1)
        for k in keys
    }
    positive = sorted(
        [(k, g) for k, g in gaps.items() if g > 0], key=lambda x: x[1], reverse=True
    )
    return [k for k, _ in positive[:top_k]], gaps


async def run_guide(
    *,
    store: CatalogStore | None,
    user_id: uuid.UUID,
    current_disposition: dict[str, float],
    current_interest: dict[str, float],
    target_disposition: dict[str, float],
    target_interest: dict[str, float],
    ideal_type: str,
    reasoning: str,
) -> Guide:
    """심화(성향 갭)·확장(도메인 상향) 타깃 선정 → 그래프 실행 → Guide."""
    deepen_targets, deepen_gaps = _positive_gaps(
        DISPOSITION_AXES, current_disposition, target_disposition, DEEPEN_TOP_K
    )
    expand_domains, expand_gaps = _positive_gaps(
        INTEREST_DOMAINS, current_interest, target_interest, EXPAND_TOP_K
    )

    if not deepen_targets and not expand_domains:
        return Guide(
            summary="현재 프로필이 이미 이상향에 가깝습니다. 지금 습관을 유지하세요.",
            steps=[],
        )

    initial: GuideState = {
        "user_id": user_id,
        "ideal_type": ideal_type,
        "reasoning": reasoning,
        "deepen_targets": deepen_targets,
        "deepen_gaps": deepen_gaps,
        "expand_domains": expand_domains,
        "expand_gaps": expand_gaps,
        "evidence": {},
        "bridge_evidence": {},
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
