"""
Navigator Agent - Schemas
Dual-Layer 아키텍처 v1.1 (2026-06-08)

Layer A: Profiler 8각 (행동 측정 · Profiler v1.1)
Layer B: 인지주권 4지표 (Profiler v1.1 산출 · Navigator 읽기 전용)
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────
# Layer A 축 정의
# ──────────────────────────────────────────


class AxisKey(str, Enum):
    INTELLECTUAL_CURIOSITY = "intellectual_curiosity"   # 1. 지적 호기심
    SELF_IMPROVEMENT       = "self_improvement"         # 2. 자기계발
    SOCIAL_AWARENESS       = "social_awareness"         # 3. 사회·시선
    DEPTH_IMMERSION        = "depth_immersion"          # 4. 깊이·몰입
    PRACTICAL_ORIENTATION  = "practical_orientation"    # 5. 실용 지향
    EMOTIONAL_COMFORT      = "emotional_comfort"        # 6. 정서·위로
    CREATIVE_EXPRESSION    = "creative_expression"      # 7. 창의·표현
    ENTERTAINMENT_RELEASE  = "entertainment_release"    # 8. 오락·해방


# 각 축별 반대·확장 방향 설명 (UI·프롬프트용)
AXIS_META: dict = {
    AxisKey.INTELLECTUAL_CURIOSITY: {
        "name": "지적 호기심",
        "description": "새 채널·낯선 주제를 넓게 탐색하는 성향",
        "low_label": "좁은 탐색",
        "high_label": "넓은 탐색",
        "opposite_desc": "한 주제 깊은 몰입 (breadth → depth)",
        "expansion_desc": "타문화·이종학문으로 더 넓게",
    },
    AxisKey.SELF_IMPROVEMENT: {
        "name": "자기계발",
        "description": "습관·목표·생산성 콘텐츠 소비 성향",
        "low_label": "낮음",
        "high_label": "높음",
        "opposite_desc": "무목적 여유·놀이 소비",
        "expansion_desc": "철학적 성찰·삶의 의미 탐구",
    },
    AxisKey.SOCIAL_AWARENESS: {
        "name": "사회·시선",
        "description": "타인·세상·이슈에 관심을 갖는 성향",
        "low_label": "내면/솔로",
        "high_label": "사회/세상",
        "opposite_desc": "내면·솔로·명상 콘텐츠",
        "expansion_desc": "글로벌 시각·다문화 이해",
    },
    AxisKey.DEPTH_IMMERSION: {
        "name": "깊이·몰입",
        "description": "길게·연속으로·한 주제 깊게 소비하는 성향",
        "low_label": "얕다",
        "high_label": "깊다",
        "opposite_desc": "가볍고 다양한 탐색",
        "expansion_desc": "전문가·학문적 깊이",
    },
    AxisKey.PRACTICAL_ORIENTATION: {
        "name": "실용 지향",
        "description": "문제 해결·스킬·How-to 콘텐츠 소비 성향",
        "low_label": "낮음",
        "high_label": "높음",
        "opposite_desc": "순수 성찰·인문학",
        "expansion_desc": "고급 스킬·전문 기술 마스터리",
    },
    AxisKey.EMOTIONAL_COMFORT: {
        "name": "정서·위로",
        "description": "힐링·감성·스트레스 해소 콘텐츠 소비 성향",
        "low_label": "낮음",
        "high_label": "높음",
        "opposite_desc": "도전·비판·불편한 진실",
        "expansion_desc": "다양한 감정 스펙트럼·예술",
    },
    AxisKey.CREATIVE_EXPRESSION: {
        "name": "창의·표현",
        "description": "만들기·실험·예술 콘텐츠 소비 성향",
        "low_label": "낮음",
        "high_label": "높음",
        "opposite_desc": "수용·감상·분석 위주",
        "expansion_desc": "다른 매체·협업 창작",
    },
    AxisKey.ENTERTAINMENT_RELEASE: {
        "name": "오락·해방",
        "description": "가볍고 해방적인 콘텐츠 소비 성향",
        "low_label": "낮음",
        "high_label": "높음",
        "opposite_desc": "깊이·집중·진지한 콘텐츠",
        "expansion_desc": "다양한 장르·문화 오락",
    },
}


# ──────────────────────────────────────────
# Layer A — Profiler 8각 점수 모델
# ──────────────────────────────────────────


class RadarChart(BaseModel):
    """Layer A — Profiler 8각 레이더 차트 (Profiler v1.1)"""

    user_id: str
    intellectual_curiosity: float = Field(..., ge=0, le=100, description="지적 호기심")
    self_improvement:       float = Field(..., ge=0, le=100, description="자기계발")
    social_awareness:       float = Field(..., ge=0, le=100, description="사회·시선")
    depth_immersion:        float = Field(..., ge=0, le=100, description="깊이·몰입")
    practical_orientation:  float = Field(..., ge=0, le=100, description="실용 지향")
    emotional_comfort:      float = Field(..., ge=0, le=100, description="정서·위로")
    creative_expression:    float = Field(..., ge=0, le=100, description="창의·표현")
    entertainment_release:  float = Field(..., ge=0, le=100, description="오락·해방")

    def to_dict(self) -> dict:
        return {
            AxisKey.INTELLECTUAL_CURIOSITY: self.intellectual_curiosity,
            AxisKey.SELF_IMPROVEMENT:       self.self_improvement,
            AxisKey.SOCIAL_AWARENESS:       self.social_awareness,
            AxisKey.DEPTH_IMMERSION:        self.depth_immersion,
            AxisKey.PRACTICAL_ORIENTATION:  self.practical_orientation,
            AxisKey.EMOTIONAL_COMFORT:      self.emotional_comfort,
            AxisKey.CREATIVE_EXPRESSION:    self.creative_expression,
            AxisKey.ENTERTAINMENT_RELEASE:  self.entertainment_release,
        }


# ──────────────────────────────────────────
# Layer B — 인지주권 4지표 (Profiler v1.1 산출)
# ──────────────────────────────────────────


class ProfilerLayerB(BaseModel):
    """
    Layer B — 인지주권 4지표 (Profiler v1.1 산출)

    ⚠️ viewing_concentration: 높을수록 나쁨 (소수 채널 편중)
       나머지 3개: 높을수록 좋음
    """
    search_active_ratio:    float = Field(default=0.0, ge=0, le=1,   description="주체성 — 직접 검색 비율 (높을수록 좋음)")
    viewing_concentration:  float = Field(default=0.0, ge=0, le=1,   description="채널 편중도 — 소수 채널 집중도 (높을수록 나쁨)")
    taste_diversity_index:  float = Field(default=50.0, ge=0, le=100, description="취향 다양성 — 4종 취향 분산 (높을수록 좋음)")
    exploration_depth:      float = Field(default=0.0, ge=0, le=1,   description="탐색 깊이 — 새 주제 진입 시 깊이 (높을수록 좋음)")

    @property
    def average_health(self) -> float:
        """인지주권 건강도 평균 (viewing_concentration 역전 후 0~100 환산)"""
        return round((
            self.search_active_ratio * 100
            + (1 - self.viewing_concentration) * 100   # 방향 반전
            + self.taste_diversity_index
            + self.exploration_depth * 100
        ) / 4, 1)


# ──────────────────────────────────────────
# Profiler 전체 출력 (v1.1 JSON 계약)
# ──────────────────────────────────────────


class ProfilerData(BaseModel):
    """Profiler v1.1 출력 전체 — Navigator 수신 인터페이스"""
    user_id:        str
    computed_at:    Optional[str] = None
    layer_a:        RadarChart
    layer_b:        ProfilerLayerB     = Field(default_factory=ProfilerLayerB)
    top5_interests: list[str]          = Field(default_factory=list)
    summary:        str                = ""


# ──────────────────────────────────────────
# 이상향 모델
# ──────────────────────────────────────────


class IdealType(str, Enum):
    OPPOSITE  = "opposite"   # 반대 방향형 — 필터버블 탈출
    EXPANSION = "expansion"  # 확장 방향형 — 자연스러운 성장  ← 기본 추천
    BALANCED  = "balanced"   # 균형형      — 균형 잡힌 자아
    CUSTOM    = "custom"     # 유저 커스텀


class IdealRadarChart(BaseModel):
    """Layer A 기반 이상향 8각 레이더 차트"""

    user_id:    str
    ideal_type: IdealType
    intellectual_curiosity: float = Field(..., ge=0, le=100)
    self_improvement:       float = Field(..., ge=0, le=100)
    social_awareness:       float = Field(..., ge=0, le=100)
    depth_immersion:        float = Field(..., ge=0, le=100)
    practical_orientation:  float = Field(..., ge=0, le=100)
    emotional_comfort:      float = Field(..., ge=0, le=100)
    creative_expression:    float = Field(..., ge=0, le=100)
    entertainment_release:  float = Field(..., ge=0, le=100)
    summary:    str = Field(default="", description="이상향 한 줄 요약")
    direction:  str = Field(default="", description="방향 요약 (예: practical_orientation→OPPOSITE)")
    alpha:      float = Field(default=0.55, description="적용 강도 α")
    reasoning:  str = Field(default="", description="AI 설계 근거 (AUTO 모드 전용)")

    def to_dict(self) -> dict:
        return {
            AxisKey.INTELLECTUAL_CURIOSITY: self.intellectual_curiosity,
            AxisKey.SELF_IMPROVEMENT:       self.self_improvement,
            AxisKey.SOCIAL_AWARENESS:       self.social_awareness,
            AxisKey.DEPTH_IMMERSION:        self.depth_immersion,
            AxisKey.PRACTICAL_ORIENTATION:  self.practical_orientation,
            AxisKey.EMOTIONAL_COMFORT:      self.emotional_comfort,
            AxisKey.CREATIVE_EXPRESSION:    self.creative_expression,
            AxisKey.ENTERTAINMENT_RELEASE:  self.entertainment_release,
        }


class RadarComparison(BaseModel):
    """Layer A 현재 vs 이상향 gap"""

    user_id:   str
    current:   RadarChart
    ideal:     IdealRadarChart
    gap:       dict  = Field(default_factory=dict, description="각 축별 gap (이상향 - 현재)")
    total_gap: float = Field(default=0.0, description="전체 gap 절댓값 합계")

    def calculate_gap(self) -> "RadarComparison":
        current_dict = self.current.to_dict()
        ideal_dict   = self.ideal.to_dict()
        self.gap = {
            key: round(ideal_dict[key] - current_dict[key], 2)
            for key in current_dict
        }
        self.total_gap = round(sum(abs(v) for v in self.gap.values()), 2)
        return self


# ──────────────────────────────────────────
# 이상향 설계 요청 / 응답
# ──────────────────────────────────────────


class IdealDesignRequest(BaseModel):
    user_id:        str
    profiler_data:  ProfilerData
    top5_interests: list[str]      = Field(default_factory=list)
    user_message:   Optional[str]  = None


class IdealDesignResponse(BaseModel):
    user_id:       str
    proposals:     list[IdealRadarChart] = Field(description="반대/확장/균형 3가지 제안")
    selected:      Optional[IdealRadarChart] = None
    agent_message: str = ""


# ──────────────────────────────────────────
# 가이드 / 퀘스트
# ──────────────────────────────────────────


class Guide(BaseModel):
    user_id:        str
    title:          str
    steps:          list[str]
    target_axes:    list[AxisKey]
    estimated_days: int = Field(default=30)


class Quest(BaseModel):
    user_id:      str
    title:        str
    description:  str
    target_axis:  AxisKey
    action:       str
    reward_point: int  = Field(default=10)
    is_completed: bool = False


# ──────────────────────────────────────────
# YouTube 재생목록
# ──────────────────────────────────────────


class PlaylistItem(BaseModel):
    video_id:         str
    title:            str
    channel:          str
    duration_seconds: int
    reason:           str = Field(description="이 영상을 추천한 이유")


class Playlist(BaseModel):
    user_id:             str
    title:               str
    description:         str
    items:               list[PlaylistItem] = Field(default_factory=list)
    youtube_playlist_id: Optional[str]      = None
    ideal_type:          IdealType          = IdealType.EXPANSION
