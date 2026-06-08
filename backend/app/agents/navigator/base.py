"""
Navigator Agent - Base
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
    Playlist,
    Quest,
    RadarChart,
)
from .state import NavigatorState, NavigatorStep
from .tool import compare_radar, generate_all_ideals, generate_guide, generate_quests


class NavigatorAgent:
    """
    Navigator 에이전트 메인 클래스

    사용 예시:
        agent = NavigatorAgent()

        # 이상향 자동 설계
        result = await agent.design_ideal(
            user_id="user_123",
            current_radar=radar,
            top5_interests=["운동", "IT", "독서", "요리", "여행"],
        )

        # 대화형 이상향 설계
        async for chunk in agent.chat(state, user_message="반대 성향으로 해줘"):
            print(chunk)
    """

    def __init__(self) -> None:
        self._graph = get_navigator_graph()

    # ──────────────────────────────────────────
    # 이상향 자동 설계 (수식 기반, LLM 없이 즉시 반환)
    # ──────────────────────────────────────────

    def design_ideal_auto(
        self,
        user_id: str,
        current_radar: RadarChart,
        top5_interests: list[str],
    ) -> IdealDesignResponse:
        """
        LLM 없이 수식 기반으로 3가지 이상향 즉시 생성
        빠른 초기 제안에 사용
        """
        proposals = generate_all_ideals(current_radar)
        return IdealDesignResponse(
            user_id=user_id,
            proposals=proposals,
            agent_message="3가지 이상향을 자동으로 설계했습니다. 마음에 드는 방향을 선택하거나, 대화로 조율해보세요.",
        )

    # ──────────────────────────────────────────
    # 가이드 + 퀘스트 빠른 생성
    # ──────────────────────────────────────────

    def generate_guide_and_quests(
        self,
        user_id: str,
        current_radar: RadarChart,
        selected_ideal: IdealRadarChart,
        top5_interests: list[str],
    ) -> tuple[Guide, list[Quest]]:
        """
        이상향 확정 후 가이드 + 퀘스트 즉시 생성
        """
        comparison = compare_radar(current_radar, selected_ideal)
        guide = generate_guide(comparison, top5_interests)
        quests = generate_quests(comparison, top5_interests, count=3)
        return guide, quests

    # ──────────────────────────────────────────
    # LangGraph 전체 플로우 실행
    # ──────────────────────────────────────────

    async def run(
        self,
        user_id: str,
        current_radar: RadarChart,
        top5_interests: list[str],
        selected_ideal_type: Optional[IdealType] = None,
    ) -> NavigatorState:
        """
        Navigator 전체 워크플로우 실행
        이상향 선택 → 가이드 → 퀘스트 → 플레이리스트까지 자동 완료

        Args:
            selected_ideal_type: None이면 ADJACENT(인접형) 기본 선택
        """
        # 초기 상태
        initial_state = NavigatorState(
            user_id=user_id,
            current_radar=current_radar,
            top5_interests=top5_interests,
            is_ideal_confirmed=True,  # 자동 실행 시 바로 확정
        )

        # 이상향 미리 선택
        proposals = generate_all_ideals(current_radar)
        target_type = selected_ideal_type or IdealType.ADJACENT
        selected = next(
            (p for p in proposals if p.ideal_type == target_type),
            proposals[0],
        )
        initial_state.selected_ideal = selected
        initial_state.ideal_type = target_type
        initial_state.ideal_proposals = IdealDesignResponse(
            user_id=user_id,
            proposals=proposals,
            selected=selected,
        )

        # 그래프 실행
        result = await self._graph.ainvoke(initial_state)
        return result

    # ──────────────────────────────────────────
    # 스트리밍 대화 인터페이스
    # ──────────────────────────────────────────

    async def chat(
        self,
        state: NavigatorState,
        user_message: str,
    ) -> AsyncIterator[str]:
        """
        유저 메시지를 받아 Navigator와 대화
        이상향 조율, 선택, 확정까지 대화로 진행

        Yields: 응답 텍스트 청크
        """
        # 유저 메시지 추가
        updated_state = state.model_copy(deep=True)
        updated_state.messages.append(HumanMessage(content=user_message))

        # 특정 키워드로 이상향 확정 감지
        confirm_keywords = ["좋아", "확정", "이걸로", "결정", "선택"]
        if any(kw in user_message for kw in confirm_keywords):
            updated_state.is_ideal_confirmed = True

        # ideal_type 키워드 감지
        if "반대" in user_message or "opposite" in user_message.lower():
            _set_ideal_by_type(updated_state, IdealType.OPPOSITE)
        elif "인접" in user_message or "adjacent" in user_message.lower():
            _set_ideal_by_type(updated_state, IdealType.ADJACENT)
        elif "균형" in user_message or "balanced" in user_message.lower() or "밸런스" in user_message:
            _set_ideal_by_type(updated_state, IdealType.BALANCED)

        # 스트리밍으로 그래프 실행
        async for chunk in self._graph.astream(
            updated_state,
            stream_mode="values",
        ):
            if chunk.get("messages"):
                last_msg = chunk["messages"][-1]
                if hasattr(last_msg, "content"):
                    yield last_msg.content

    # ──────────────────────────────────────────
    # 상태 빌더 (외부에서 초기 상태 생성 시 사용)
    # ──────────────────────────────────────────

    @staticmethod
    def create_initial_state(
        user_id: str,
        current_radar: RadarChart,
        top5_interests: list[str],
    ) -> NavigatorState:
        return NavigatorState(
            user_id=user_id,
            current_radar=current_radar,
            top5_interests=top5_interests,
        )


# ──────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────


def _set_ideal_by_type(state: NavigatorState, ideal_type: IdealType) -> None:
    """대화에서 이상향 타입 선택 시 상태 업데이트"""
    if state.ideal_proposals:
        for p in state.ideal_proposals.proposals:
            if p.ideal_type == ideal_type:
                state.selected_ideal = p
                state.ideal_type = ideal_type
                break


# ──────────────────────────────────────────
# 싱글톤 인스턴스
# ──────────────────────────────────────────

_navigator_agent: Optional[NavigatorAgent] = None


def get_navigator_agent() -> NavigatorAgent:
    global _navigator_agent
    if _navigator_agent is None:
        _navigator_agent = NavigatorAgent()
    return _navigator_agent
