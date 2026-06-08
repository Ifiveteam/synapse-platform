"""
Navigator Agent - Base (Dual-Layer v1.1)
외부에서 Navigator 에이전트를 실행하는 진입점
"""

from typing import AsyncIterator, Optional

from langchain_core.messages import HumanMessage

from .graph import get_navigator_graph
from .schemas import (
    Guide,
    IdealDesignResponse,
    IdealRadarChart,
    IdealType,
    ProfilerData,
    Quest,
    RadarChart,
)
from .state import NavigatorState, NavigatorStep
from .tool import (
    compare_radar,
    compute_dominant_weak,
    enrich_quests_with_layer_b,
    generate_all_ideals,
    generate_guide,
    generate_quests,
)


class NavigatorAgent:
    """
    Navigator 에이전트 메인 클래스 (Dual-Layer v1.1)

    사용 예시:
        agent = NavigatorAgent()

        # 이상향 자동 설계 (Profiler v1.1 데이터 수신)
        result = agent.design_ideal_auto(
            user_id="user_123",
            profiler_data=profiler_data,
            top5_interests=["운동", "IT", "독서"],
        )
    """

    def __init__(self) -> None:
        self._graph = get_navigator_graph()

    # ──────────────────────────────────────────
    # 이상향 자동 설계 (수식 기반, LLM 없이 즉시 반환)
    # ──────────────────────────────────────────

    def design_ideal_auto(
        self,
        user_id:        str,
        profiler_data:  ProfilerData,
        top5_interests: list[str],
    ) -> IdealDesignResponse:
        """
        LLM 없이 수식 기반으로 3가지 이상향 즉시 생성
        layer_a에서 dominant/weak 런타임 계산 후 이중 방향 적용
        """
        dominant, weak = compute_dominant_weak(profiler_data.layer_a)
        proposals = generate_all_ideals(profiler_data.layer_a, dominant, weak)
        return IdealDesignResponse(
            user_id=user_id,
            proposals=proposals,
            agent_message=(
                "3가지 이상향을 자동으로 설계했습니다. "
                "마음에 드는 방향을 선택하거나, 대화로 조율해보세요."
            ),
        )

    # ──────────────────────────────────────────
    # 가이드 + 퀘스트 빠른 생성
    # ──────────────────────────────────────────

    def generate_guide_and_quests(
        self,
        profiler_data:  ProfilerData,
        selected_ideal: IdealRadarChart,
        top5_interests: list[str],
    ) -> tuple[Guide, list[Quest]]:
        """이상향 확정 후 가이드 + 퀘스트 즉시 생성 (Layer B 보강 포함)"""
        comparison = compare_radar(profiler_data.layer_a, selected_ideal)
        guide      = generate_guide(comparison, top5_interests)
        quests     = generate_quests(comparison, top5_interests, count=3)
        quests     = enrich_quests_with_layer_b(quests, profiler_data.layer_b)
        return guide, quests

    # ──────────────────────────────────────────
    # LangGraph 전체 플로우 실행
    # ──────────────────────────────────────────

    async def run(
        self,
        user_id:             str,
        profiler_data:       ProfilerData,
        top5_interests:      list[str],
        selected_ideal_type: Optional[IdealType] = None,
    ) -> NavigatorState:
        """Navigator 전체 워크플로우 실행"""
        dominant, weak = compute_dominant_weak(profiler_data.layer_a)
        proposals      = generate_all_ideals(profiler_data.layer_a, dominant, weak)
        target_type    = selected_ideal_type or IdealType.EXPANSION
        selected       = next((p for p in proposals if p.ideal_type == target_type), proposals[0])

        initial_state = NavigatorState(
            user_id            = user_id,
            current_radar      = profiler_data.layer_a,
            layer_b            = profiler_data.layer_b,
            top5_interests     = top5_interests,
            is_ideal_confirmed = True,
            selected_ideal     = selected,
            ideal_type         = target_type,
            ideal_proposals    = IdealDesignResponse(
                user_id=user_id,
                proposals=proposals,
                selected=selected,
            ),
        )

        result = await self._graph.ainvoke(initial_state)
        return result

    # ──────────────────────────────────────────
    # 스트리밍 대화
    # ──────────────────────────────────────────

    async def chat(
        self,
        state:        NavigatorState,
        user_message: str,
    ) -> AsyncIterator[str]:
        """유저 메시지를 받아 Navigator와 대화"""
        updated_state = state.model_copy(deep=True)
        updated_state.messages.append(HumanMessage(content=user_message))

        confirm_keywords = ["좋아", "확정", "이걸로", "결정", "선택"]
        if any(kw in user_message for kw in confirm_keywords):
            updated_state.is_ideal_confirmed = True

        if "반대" in user_message or "opposite" in user_message.lower():
            _set_ideal_by_type(updated_state, IdealType.OPPOSITE)
        elif "확장" in user_message or "expansion" in user_message.lower():
            _set_ideal_by_type(updated_state, IdealType.EXPANSION)
        elif "균형" in user_message or "balanced" in user_message.lower() or "밸런스" in user_message:
            _set_ideal_by_type(updated_state, IdealType.BALANCED)

        async for chunk in self._graph.astream(updated_state, stream_mode="values"):
            if chunk.get("messages"):
                last_msg = chunk["messages"][-1]
                if hasattr(last_msg, "content"):
                    yield last_msg.content

    # ──────────────────────────────────────────
    # 초기 상태 빌더
    # ──────────────────────────────────────────

    @staticmethod
    def create_initial_state(
        user_id:        str,
        profiler_data:  ProfilerData,
        top5_interests: list[str],
    ) -> NavigatorState:
        return NavigatorState(
            user_id        = user_id,
            current_radar  = profiler_data.layer_a,
            layer_b        = profiler_data.layer_b,
            top5_interests = top5_interests,
        )


# ──────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────


def _set_ideal_by_type(state: NavigatorState, ideal_type: IdealType) -> None:
    if state.ideal_proposals:
        for p in state.ideal_proposals.proposals:
            if p.ideal_type == ideal_type:
                state.selected_ideal = p
                state.ideal_type     = ideal_type
                break


# ──────────────────────────────────────────
# 싱글톤
# ──────────────────────────────────────────

_navigator_agent: Optional[NavigatorAgent] = None


def get_navigator_agent() -> NavigatorAgent:
    global _navigator_agent
    if _navigator_agent is None:
        _navigator_agent = NavigatorAgent()
    return _navigator_agent
