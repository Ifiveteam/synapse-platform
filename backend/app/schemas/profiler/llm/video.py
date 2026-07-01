from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, Field, field_validator

# ── 고정 어휘 (각 10개) — LLM이 자유작문 대신 이 목록에서만 분류 ──
ToneLabel = Literal[
    "차분한",
    "활기찬",
    "진지한",
    "유머러스",
    "따뜻한",
    "자극적",
    "비판적",
    "감성적",
    "정보적",
    "영감적",
]
IntentLabel = Literal[
    "정보전달",
    "학습",
    "오락",
    "동기부여",
    "공감",
    "설득",
    "영감",
    "휴식",
    "토론",
    "트렌드",
]
ValueLabel = Literal[
    "성장",
    "효율",
    "자유",
    "공동체",
    "안정",
    "도전",
    "심미",
    "정의",
    "전통",
    "자기표현",
]

TONES: tuple[str, ...] = get_args(ToneLabel)
INTENTS: tuple[str, ...] = get_args(IntentLabel)
VALUES: tuple[str, ...] = get_args(ValueLabel)


class VideoSemanticAnalysis(BaseModel):
    """영상 1건의 의미분석 (Gemini structured output) — 라벨은 고정 어휘에서 선택."""

    summary_kr: str = Field(
        ...,
        description=(
            "유저 성향 추론용 시맨틱 브리프. 3~5문장(200~400자): "
            "주제·도메인 → 시청 동기 → 인지·소비 방식 → 감정·톤 맥락 → 가치·태도 순. "
            "라벨(tones/intents/value_signals)과 같은 단어 반복 금지."
        ),
    )
    tones: list[ToneLabel] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="톤/분위기 — 고정 어휘에서 가장 맞는 것 3개",
    )
    intents: list[IntentLabel] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="시청 의도 — 고정 어휘에서 가장 맞는 것 3개",
    )
    value_signals: list[ValueLabel] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="가치 신호 — 고정 어휘에서 가장 맞는 것 3개",
    )

    @field_validator("tones", "intents", "value_signals")
    @classmethod
    def _dedup_max3(cls, v: list[str]) -> list[str]:
        seen: list[str] = []
        for s in v:
            if s not in seen:
                seen.append(s)
        return seen[:3]


class VideoAnalysisItem(VideoSemanticAnalysis):
    """배치 분석 내 영상 1건 — index로 입력 영상([N])과 매핑."""

    index: int = Field(..., description="입력 영상 번호 ([N]으로 표기된 그 번호)")


class VideoBatchAnalysis(BaseModel):
    """여러 영상 배치 분석 결과 — 입력한 각 영상마다 1건."""

    items: list[VideoAnalysisItem] = Field(
        ..., description="입력한 각 영상([N])마다 1건씩, index로 매핑"
    )
