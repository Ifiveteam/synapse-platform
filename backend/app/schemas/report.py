"""대시보드 바인딩용 B2B 트렌드 리포트 Structured Output 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CognitiveAxisScore(BaseModel):
    subject: str = Field(..., description="8각 성향 축의 한국어 라벨 (예: 지적 호기심, 자기계발)")
    key: str = Field(..., description="8각 성향 축의 영문 키 (예: intellectual_curiosity, self_improvement)")
    score: float = Field(..., description="0~100 사이의 코호트 평균 점수")
    interpretation: str = Field(..., description="해당 축 점수에 대한 짧은 분석 및 해석 (1문장)")


class KeywordItem(BaseModel):
    rank: int = Field(..., description="1부터 5까지의 순위")
    keyword: str = Field(..., description="키워드 명")
    metrics: str = Field(..., description="빈도수 또는 조회수/출처 정보")
    change: str = Field(..., description="전주 대비 변화율 또는 트렌드 지표")


class GapAnalysis(BaseModel):
    intersection_keywords: list[str] = Field(
        ..., description="내부와 외부가 공통으로 관심을 갖는 교집합 키워드 리스트 (최대 3개)"
    )
    intersection_interpretation: str = Field(
        ..., description="교집합 영역에 대한 B2B 관점의 해석"
    )
    internal_only_keywords: list[str] = Field(
        ..., description="내부 코호트만 고도로 집중하는 우세 키워드 리스트 (최대 3개)"
    )
    internal_only_interpretation: str = Field(
        ..., description="내부 우세 현상과 성향 간의 연결고리 해석"
    )
    external_only_keywords: list[str] = Field(
        ..., description="외부 대중/뉴스만 반응하는 우세 키워드 리스트 (최대 3개)"
    )
    external_only_interpretation: str = Field(
        ..., description="외부 우세 현상과 내부 관심사 간의 단절/격차 해석"
    )
    filter_bubble_scenario: str = Field(
        ..., description="격차로 인해 발생하는 맥락적 필터 버블 시나리오 심층 종합 해석 (2~3문장)"
    )


class B2BRecommendations(BaseModel):
    content_strategy: list[str] = Field(
        ..., description="콘텐츠 기획 및 확장 방향 액션 가이드 (2~3개)"
    )
    marketing: list[str] = Field(
        ..., description="광고 집행 및 타겟 오디언스 공략 가이드 (2~3개)"
    )
    platform_policy: list[str] = Field(
        ..., description="플랫폼 정책 및 미디어 중립성 개선 가이드 (2~3개)"
    )


class DashboardReportSchema(BaseModel):
    headline_summary: str = Field(
        ..., description="포털 메인 헤드라인 스타일의 굵고 직관적인 한 줄 요약 카피"
    )
    neutrality_score: int = Field(..., description="0~100 사이의 미디어 중립성 종합 점수")
    neutrality_status: str = Field(
        ..., description="점수에 따른 상태 분류 (안정, 주의, 위험 중 택1)"
    )
    neutrality_reason: str = Field(
        ..., description="중립성 점수 및 상태에 대한 핵심 요약 배경 (1문장)"
    )
    radar_chart_data: list[CognitiveAxisScore] = Field(
        ..., description="Recharts RadarChart에 바로 바인딩할 수 있는 8개 성향 축 데이터"
    )
    dominant_axes: list[str] = Field(
        ..., description="70점 내외 혹은 상대적으로 가장 높은 우세 성향 축 명칭 리스트"
    )
    deficient_axes: list[str] = Field(
        ..., description="40점 내외 혹은 상대적으로 가장 낮은 저조 성향 축 명칭 리스트"
    )
    macro_trend_internal: list[KeywordItem] = Field(
        ..., description="내부 유저 상위 키워드 TOP 5"
    )
    macro_trend_external: list[KeywordItem] = Field(
        ..., description="외부 시장 급상승 키워드 TOP 5"
    )
    gap_analysis: GapAnalysis = Field(
        ..., description="내/외부 데이터 매칭 및 격차 해석 데이터"
    )
    recommendations: B2BRecommendations = Field(
        ..., description="태스크별로 분류된 3대 액션 플랜 가이드"
    )
