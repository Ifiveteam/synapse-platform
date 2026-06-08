"""
Navigator Agent - Schemas
8각 레이더 차트 축 데이터 구조 정의

축 타입:
  A (성장축)     - 높을수록 좋음, 항상 높은 방향으로 유도
  B (스펙트럼축) - 양극단 스펙트럼, 치우치면 반대 방향으로 유도
  C (확장축)     - 인접 영역으로 뻗어나감
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────
# 축 정의
# ──────────────────────────────────────────


class AxisType(str, Enum):
    GROWTH = "growth"        # A: 성장축 - 높을수록 좋음
    SPECTRUM = "spectrum"    # B: 스펙트럼축 - 반대 방향 유도
    EXPANSION = "expansion"  # C: 확장축 - 인접 영역 탐색


class AxisKey(str, Enum):
    PERSPECTIVE_BALANCE = "perspective_balance"    # 1. 관점 균형 (A)
    AUTONOMY = "autonomy"                           # 2. 주체성 (A)
    EXPLORATION_WIDTH = "exploration_width"         # 3. 탐색의 넓이 (C)
    DEPTH_IMMERSION = "depth_immersion"             # 4. 몰입의 깊이 (C)
    EMOTIONAL_CHALLENGE = "emotional_challenge"     # 5. 정서 ↔ 도전 (B)
    PRACTICAL_REFLECTION = "practical_reflection"   # 6. 실용 ↔ 성찰 (B)
    INDIVIDUAL_SOCIAL = "individual_social"         # 7. 개인 ↔ 사회 (B)
    CONSUME_CREATE = "consume_create"               # 8. 소비 ↔ 창조 (B)


# ──────────────────────────────────────────
# 축 메타데이터
# ──────────────────────────────────────────


AXIS_META: dict = {
    AxisKey.PERSPECTIVE_BALANCE: {
        "name": "관점 균형",
        "type": AxisType.GROWTH,
        "description": "같은 주제에서 반대 입장을 얼마나 보는가",
        "low_label": "편향",
        "high_label": "균형",
        "measure": "입장 분포 비율",
        "ideal_direction": "항상 균형 방향",
        "recommend_hint": "반대 입장 콘텐츠 추천",
    },
    AxisKey.AUTONOMY: {
        "name": "주체성",
        "type": AxisType.GROWTH,
        "description": "내가 선택하는가, 알고리즘이 선택하는가",
        "low_label": "수동",
        "high_label": "능동",
        "measure": "검색 vs 추천 비율",
        "ideal_direction": "항상 능동 방향",
        "recommend_hint": "직접 탐색 유도, 새로운 검색어 제안",
    },
    AxisKey.EXPLORATION_WIDTH: {
        "name": "탐색의 넓이",
        "type": AxisType.EXPANSION,
        "description": "얼마나 다양한 분야를 탐색하는가",
        "low_label": "좁다",
        "high_label": "넓다",
        "measure": "카테고리 분산도 + 신규 채널 비율",
        "ideal_direction": "현재 관심사 인접 영역으로 확장",
        "recommend_hint": "현재 관심사와 연결된 새로운 분야",
    },
    AxisKey.DEPTH_IMMERSION: {
        "name": "몰입의 깊이",
        "type": AxisType.EXPANSION,
        "description": "얼마나 집중해서 한 주제를 깊게 파고드는가",
        "low_label": "얕다",
        "high_label": "깊다",
        "measure": "체류시간 + 연속시청 + 콘텐츠 길이",
        "ideal_direction": "현재 관심 분야 심화 탐색",
        "recommend_hint": "현재 소비 중인 주제의 심층 콘텐츠",
    },
    AxisKey.EMOTIONAL_CHALLENGE: {
        "name": "정서 ↔ 도전",
        "type": AxisType.SPECTRUM,
        "description": "정서적 위로를 추구하는가, 도전적 자극을 추구하는가",
        "low_label": "정서/위로",
        "high_label": "도전/자극",
        "measure": "힐링/ASMR vs 도전/비판 콘텐츠 비율",
        "ideal_direction": "치우친 반대 방향으로 유도",
        "recommend_hint": "정서 치우침→도전 콘텐츠 / 도전 치우침→힐링 콘텐츠",
    },
    AxisKey.PRACTICAL_REFLECTION: {
        "name": "실용 ↔ 성찰",
        "type": AxisType.SPECTRUM,
        "description": "실용적 방법을 추구하는가, 철학적 성찰을 추구하는가",
        "low_label": "실용/방법",
        "high_label": "성찰/철학",
        "measure": "튜토리얼/How-to vs 철학/인문 콘텐츠 비율",
        "ideal_direction": "치우친 반대 방향으로 유도",
        "recommend_hint": "실용 치우침→성찰 콘텐츠 / 성찰 치우침→실용 콘텐츠",
    },
    AxisKey.INDIVIDUAL_SOCIAL: {
        "name": "개인 ↔ 사회",
        "type": AxisType.SPECTRUM,
        "description": "내면/개인적 콘텐츠를 보는가, 사회/세상을 바라보는가",
        "low_label": "내면/솔로",
        "high_label": "사회/세상",
        "measure": "개인 취미/일상 vs 뉴스/다큐/시사 비율",
        "ideal_direction": "치우친 반대 방향으로 유도",
        "recommend_hint": "개인 치우침→사회 이슈 / 사회 치우침→내면 성장",
    },
    AxisKey.CONSUME_CREATE: {
        "name": "소비 ↔ 창조",
        "type": AxisType.SPECTRUM,
        "description": "수동적으로 받아먹는가, 능동적으로 탐구/창작하는가",
        "low_label": "수동소비",
        "high_label": "능동창조",
        "measure": "검색 + 스크랩 + 창작 콘텐츠 소비 비율",
        "ideal_direction": "치우친 반대 방향으로 유도",
        "recommend_hint": "소비 치우침→창작/DIY / 창조 치우침→큐레이션 휴식",
    },
}


# ──────────────────────────────────────────
# 점수 모델
# ──────────────────────────────────────────


class RadarChart(BaseModel):
    """8각 레이더 차트 전체 데이터"""

    user_id: str
    perspective_balance: float = Field(..., ge=0, le=100, description="관점 균형")
    autonomy: float = Field(..., ge=0, le=100, description="주체성")
    exploration_width: float = Field(..., ge=0, le=100, description="탐색의 넓이")
    depth_immersion: float = Field(..., ge=0, le=100, description="몰입의 깊이")
    emotional_challenge: float = Field(..., ge=0, le=100, description="정서 ↔ 도전")
    practical_reflection: float = Field(..., ge=0, le=100, description="실용 ↔ 성찰")
    individual_social: float = Field(..., ge=0, le=100, description="개인 ↔ 사회")
    consume_create: float = Field(..., ge=0, le=100, description="소비 ↔ 창조")

    def to_dict(self) -> dict:
        return {
            AxisKey.PERSPECTIVE_BALANCE: self.perspective_balance,
            AxisKey.AUTONOMY: self.autonomy,
            AxisKey.EXPLORATION_WIDTH: self.exploration_width,
            AxisKey.DEPTH_IMMERSION: self.depth_immersion,
            AxisKey.EMOTIONAL_CHALLENGE: self.emotional_challenge,
            AxisKey.PRACTICAL_REFLECTION: self.practical_reflection,
            AxisKey.INDIVIDUAL_SOCIAL: self.individual_social,
            AxisKey.CONSUME_CREATE: self.consume_create,
        }


# ──────────────────────────────────────────
# 이상향 모델
# ──────────────────────────────────────────


class IdealType(str, Enum):
    OPPOSITE = "opposite"    # 반대 성향형 - 필터버블 완전 탈출
    ADJACENT = "adjacent"    # 인접 확장형 - 자연스러운 성장
    BALANCED = "balanced"    # 밸런스형   - 균형 잡힌 자아
    CUSTOM = "custom"        # 유저 커스텀


class IdealRadarChart(BaseModel):
    """이상향 8각 레이더 차트"""

    user_id: str
    ideal_type: IdealType
    perspective_balance: float = Field(..., ge=0, le=100)
    autonomy: float = Field(..., ge=0, le=100)
    exploration_width: float = Field(..., ge=0, le=100)
    depth_immersion: float = Field(..., ge=0, le=100)
    emotional_challenge: float = Field(..., ge=0, le=100)
    practical_reflection: float = Field(..., ge=0, le=100)
    individual_social: float = Field(..., ge=0, le=100)
    consume_create: float = Field(..., ge=0, le=100)
    summary: str = Field(default="", description="이상향 한 줄 요약")

    def to_dict(self) -> dict:
        return {
            AxisKey.PERSPECTIVE_BALANCE: self.perspective_balance,
            AxisKey.AUTONOMY: self.autonomy,
            AxisKey.EXPLORATION_WIDTH: self.exploration_width,
            AxisKey.DEPTH_IMMERSION: self.depth_immersion,
            AxisKey.EMOTIONAL_CHALLENGE: self.emotional_challenge,
            AxisKey.PRACTICAL_REFLECTION: self.practical_reflection,
            AxisKey.INDIVIDUAL_SOCIAL: self.individual_social,
            AxisKey.CONSUME_CREATE: self.consume_create,
        }


class RadarComparison(BaseModel):
    """현재 vs 이상향 비교"""

    user_id: str
    current: RadarChart
    ideal: IdealRadarChart
    gap: dict = Field(default_factory=dict, description="각 축별 gap")
    total_gap: float = Field(default=0.0, description="전체 gap 합계")

    def calculate_gap(self) -> "RadarComparison":
        current_dict = self.current.to_dict()
        ideal_dict = self.ideal.to_dict()
        self.gap = {
            key: round(ideal_dict[key] - current_dict[key], 2)
            for key in current_dict
        }
        self.total_gap = round(sum(abs(v) for v in self.gap.values()), 2)
        return self


# ──────────────────────────────────────────
# 이상향 설계 요청/응답
# ──────────────────────────────────────────


class IdealDesignRequest(BaseModel):
    """이상향 설계 요청"""

    user_id: str
    current_radar: RadarChart
    top5_interests: list[str] = Field(default_factory=list)
    user_message: Optional[str] = None


class IdealDesignResponse(BaseModel):
    """이상향 설계 응답 - 3가지 제안"""

    user_id: str
    proposals: list[IdealRadarChart] = Field(description="반대/인접/밸런스 3가지 제안")
    selected: Optional[IdealRadarChart] = None
    agent_message: str = ""


# ──────────────────────────────────────────
# 가이드 / 퀘스트
# ──────────────────────────────────────────


class Guide(BaseModel):
    """버블 탈출 가이드"""

    user_id: str
    title: str
    steps: list[str]
    target_axes: list[AxisKey]
    estimated_days: int = Field(default=30)


class Quest(BaseModel):
    """일일 퀘스트"""

    user_id: str
    title: str
    description: str
    target_axis: AxisKey
    action: str
    reward_point: int = Field(default=10)
    is_completed: bool = False


# ──────────────────────────────────────────
# YouTube 재생목록
# ──────────────────────────────────────────


class PlaylistItem(BaseModel):
    """재생목록 아이템"""

    video_id: str
    title: str
    channel: str
    duration_seconds: int
    reason: str = Field(description="이 영상을 추천한 이유")


class Playlist(BaseModel):
    """이상향 기반 재생목록"""

    user_id: str
    title: str
    description: str
    items: list[PlaylistItem] = Field(default_factory=list)
    youtube_playlist_id: Optional[str] = None
    ideal_type: IdealType = IdealType.ADJACENT
