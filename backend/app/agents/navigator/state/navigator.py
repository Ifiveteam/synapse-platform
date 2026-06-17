"""
Navigator Agent - State
LangGraph 워크플로우 상태 정의 (Dual-Layer v1.1)
"""

from typing import Annotated, Optional

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.agents.navigator.schemas import (
    Guide,
    IdealDesignResponse,
    IdealRadarChart,
    IdealType,
    Playlist,
    ProfilerLayerB,
    Quest,
    RadarChart,
    RadarComparison,
)

# ──────────────────────────────────────────
# Navigator 워크플로우 단계
# ──────────────────────────────────────────


class NavigatorStep(str):
    INIT = "init"
    ANALYZE_PROFILE = "analyze_profile"  # Profiler v1.1 데이터 수신 확인
    GENERATE_IDEALS = "generate_ideals"  # 8축 이중 방향 기반 이상향 3종 생성
    CHAT_DESIGN = "chat_design"  # 대화형 이상향 조율
    CONFIRM_IDEAL = "confirm_ideal"  # 이상향 확정 + gap 계산
    GENERATE_GUIDE = "generate_guide"  # 30일 가이드 생성
    GENERATE_QUEST = "generate_quest"  # 오늘의 퀘스트 생성
    BUILD_PLAYLIST = "build_playlist"  # YouTube 큐레이션
    COMPLETE = "complete"


# ──────────────────────────────────────────
# Navigator 상태 (v1.1)
# ──────────────────────────────────────────


class NavigatorState(BaseModel):
    """
    Navigator 에이전트 전체 상태 (Dual-Layer v1.1)

    Layer A: current_radar   — Profiler 8각 (행동 측정)
    Layer B: layer_b         — 인지주권 4지표 (Profiler v1.1 산출)
    이상향:   축별 OPPOSITE / EXPANSION 방향 + α 강도
    """

    # ── 기본 정보 ──
    user_id: str
    top5_interests: list[str] = Field(default_factory=list)

    # ── Layer A: Profiler 8각 ──
    current_radar: Optional[RadarChart] = None

    # ── Layer B: 인지주권 4지표 (Profiler v1.1 산출, Navigator 읽기 전용) ──
    layer_b: Optional[ProfilerLayerB] = None

    # ── 이상향 설계 ──
    ideal_proposals: Optional[IdealDesignResponse] = None
    selected_ideal: Optional[IdealRadarChart] = None
    ideal_type: Optional[IdealType] = None

    # ── gap ──
    comparison: Optional[RadarComparison] = None

    # ── 대화 메시지 ──
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # ── 생성 결과물 ──
    guide: Optional[Guide] = None
    quests: list[Quest] = Field(default_factory=list)
    playlist: Optional[Playlist] = None

    # ── 워크플로우 상태 ──
    current_step: str = NavigatorStep.INIT
    is_ideal_confirmed: bool = False
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
