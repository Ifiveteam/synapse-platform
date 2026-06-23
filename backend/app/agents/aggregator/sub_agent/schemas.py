"""서브 에이전트 Structured Output 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.agents.aggregator.state.types import REVIEW_PASS_THRESHOLD, RevisionTarget

_CULTURE_FEEDBACK_MARKERS: tuple[str, ...] = (
    "문화",
    "콘텐츠",
    "youtube",
    "유튜브",
    "8각",
    "성향",
    "culture",
    "인지",
    "코호트",
)
_MARKET_FEEDBACK_MARKERS: tuple[str, ...] = (
    "매크로",
    "시장",
    "뉴스",
    "google",
    "naver",
    "경제",
    "언론",
    "market",
    "시사",
    "트렌드 rss",
)


class VerificationResult(BaseModel):
    """시니어 검수자 에이전트 구조화 출력."""

    verification_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="리포트 품질 종합 점수 (0~100)",
    )
    critique_feedback: str = Field(
        default="",
        description="80점 미만 시 반려 사유·수정 지침. 합격 시 통과 평 또는 빈 문자열",
    )
    is_template_valid: bool = Field(
        ...,
        description="DashboardReportSchema 필드·개수·대시보드 바인딩 준수 여부",
    )
    revision_target: RevisionTarget = Field(
        default="generate_report",
        description=(
            "반려 시 재실행 노드. "
            "culture_analysis=문화/8각/YouTube 초안 문제, "
            "market_analysis=매크로/뉴스 초안 문제, "
            "both_analyses=양쪽 초안 문제, "
            "generate_report=융합·서식·최종 리포트 문제"
        ),
    )

    @field_validator("verification_score", mode="before")
    @classmethod
    def clamp_score(cls, value: object) -> int:
        score = int(value)  # type: ignore[arg-type]
        return max(0, min(100, score))

    @field_validator("critique_feedback", mode="before")
    @classmethod
    def normalize_feedback(cls, value: object) -> str:
        return str(value or "").strip()

    def resolve_revision_target(self) -> RevisionTarget:
        """Structured Output + 피드백 키워드를 결합해 결정론적으로 재실행 노드를 결정."""
        if self.verification_score >= REVIEW_PASS_THRESHOLD:
            return "generate_report"

        feedback_lower = self.critique_feedback.lower()
        culture_hit = any(
            marker in feedback_lower for marker in _CULTURE_FEEDBACK_MARKERS
        )
        market_hit = any(
            marker in feedback_lower for marker in _MARKET_FEEDBACK_MARKERS
        )

        if culture_hit and market_hit:
            return "both_analyses"
        if culture_hit and not market_hit:
            return "culture_analysis"
        if market_hit and not culture_hit:
            return "market_analysis"

        if not self.is_template_valid:
            return "generate_report"

        return self.revision_target
