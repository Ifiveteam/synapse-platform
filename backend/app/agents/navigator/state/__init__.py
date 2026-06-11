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
    ProfilerData,
    ProfilerLayerB,
    Quest,
    RadarChart,
    RadarComparison,
)


class NavigatorStep(str):
    INIT            = "init"
    ANALYZE_PROFILE = "analyze_profile"
    GENERATE_IDEALS = "generate_ideals"
    CHAT_DESIGN     = "chat_design"
    CONFIRM_IDEAL   = "confirm_ideal"
    GENERATE_GUIDE  = "generate_guide"
    GENERATE_QUEST  = "generate_quest"
    BUILD_PLAYLIST  = "build_playlist"
    COMPLETE        = "complete"


class NavigatorState(BaseModel):
    user_id:        str
    top5_interests: list[str] = Field(default_factory=list)

    current_radar: Optional[RadarChart]    = None
    layer_b: Optional[ProfilerLayerB] = None

    ideal_proposals: Optional[IdealDesignResponse] = None
    selected_ideal:  Optional[IdealRadarChart]     = None
    ideal_type:      Optional[IdealType]           = None

    comparison: Optional[RadarComparison] = None

    messages: Annotated[list, add_messages] = Field(default_factory=list)

    guide:    Optional[Guide]    = None
    quests:   list[Quest]        = Field(default_factory=list)
    playlist: Optional[Playlist] = None

    current_step:       str  = NavigatorStep.INIT
    is_ideal_confirmed: bool = False
    error:              Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
