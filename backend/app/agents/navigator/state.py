"""
Navigator Agent - State
LangGraph 워크플로우 상태 정의
"""

from typing import Annotated, Optional
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from .schemas import (
    Guide,
    IdealDesignResponse,
    IdealRadarChart,
    IdealType,
    Playlist,
    Quest,
    RadarChart,
    RadarComparison,
)


# ──────────────────────────────────────────
# Navigator 워크플로우 단계
# ──────────────────────────────────────────


class NavigatorStep(str):
    INIT = "init"                          # 초기화
    ANALYZE_PROFILE = "analyze_profile"    # 프로파일 분석
    GENERATE_IDEALS = "generate_ideals"    # 이상향 3종 자동 생성
    CHAT_DESIGN = "chat_design"            # 대화형 이상향 설계
    CONFIRM_IDEAL = "confirm_ideal"        # 이상향 확정
    GENERATE_GUIDE = "generate_guide"      # 가이드 생성
    GENERATE_QUEST = "generate_quest"      # 퀘스트 생성
    BUILD_PLAYLIST = "build_playlist"      # 재생목록 생성
    COMPLETE = "complete"                  # 완료


# ──────────────────────────────────────────
# Navigator 상태
# ──────────────────────────────────────────


class NavigatorState(BaseModel):
    """Navigator 에이전트 전체 상태"""

    # 유저 정보
    user_id: str
    top5_interests: list[str] = Field(default_factory=list)

    # 현재 프로필 (프로파일러에게서 수신)
    current_radar: Optional[RadarChart] = None

    # 이상향 설계
    ideal_proposals: Optional[IdealDesignResponse] = None  # 3가지 자동 제안
    selected_ideal: Optional[IdealRadarChart] = None        # 유저가 선택한 이상향
    ideal_type: Optional[IdealType] = None

    # 현재 vs 이상향 비교
    comparison: Optional[RadarComparison] = None

    # 대화 메시지 (LangGraph add_messages reducer 사용)
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # 생성된 결과물
    guide: Optional[Guide] = None
    quests: list[Quest] = Field(default_factory=list)
    playlist: Optional[Playlist] = None

    # 워크플로우 상태
    current_step: str = NavigatorStep.INIT
    is_ideal_confirmed: bool = False
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
