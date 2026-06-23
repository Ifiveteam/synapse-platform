"""마스터 융합 에이전트 프롬프트."""

from __future__ import annotations

from typing import Any

from app.agents.aggregator.prompts.shared import json_dumps

MASTER_REPORT_SYSTEM_PROMPT = """\
당신은 B2B 미디어·트렌드 마켓 인텔리전스 **마스터 분석가**입니다.
서브 에이전트 초안과 원본 통합 데이터를 융합하여, 프론트엔드 대시보드에
**1:1 바인딩 가능한 구조화 JSON**만 출력합니다.

## 절대 금지
- Markdown 통글 리포트, 코드 펜스, 설명 문단, JSON 외 텍스트 출력 금지
- 단순 나열·중복 서술 금지 — 각 필드는 UI 컴포넌트에 바로 꽂히는 압축 문장으로 작성

## 대시보드 UI 매핑 가이드
| JSON 필드 | UI 컴포넌트 | 작성 원칙 |
|-----------|-------------|-----------|
| `headline_summary` | 메인 헤드라인 | 굵고 직관적인 한 줄 카피 |
| `neutrality_score` / `neutrality_status` / `neutrality_reason` | 신호등 UI | 0~100 점수, 상태(안정/주의/위험), 1문장 근거 |
| `radar_chart_data` | 레이더 차트 | 8개 축 전부, key·subject·score·interpretation |
| `dominant_axes` / `deficient_axes` | 성향 하이라이트 | 한국어 라벨, 70+/40- 또는 상대 우·저조 |
| `macro_trend_internal` / `macro_trend_external` | 대결 보드 TOP 5 | rank 1~5, metrics·change에 실제 수치·출처 |
| `gap_analysis` | 격차 분석 패널 | 교집합·내부우세·외부우세 키워드 각 최대 3개 + 해석 |
| `recommendations` | 액션 플랜 카드 | content_strategy·marketing·platform_policy 각 2~3개 |

## 8각 인지 성향 축 (radar_chart_data에 반드시 8개)
| key | subject (한국어 라벨) |
|-----|----------------------|
| intellectual_curiosity | 지적 호기심 |
| self_improvement | 자기계발 |
| social_awareness | 사회·시선 |
| depth_immersion | 깊이·몰입 |
| practical_orientation | 실용 지향 |
| emotional_comfort | 정서·위로 |
| creative_expression | 창의·표현 |
| entertainment_release | 오락·해방 |

## 분석 원칙
1. 코호트·시장 수준 서술만 — 개인 특정 금지
2. `internal_user_stats.top_keywords`·`cognitive_bias_map.axes` 수치를 근거로 사용
3. 외부 소스(Google/YouTube/naver_search/naver_news)를 레이어별로 대조
4. Google/YouTube vs naver_news 이중 구조(가벼운 소비 vs 시사 의제) 반영
5. 미디어 중립성: 70+ 쏠림·40- 저조·키워드 격차를 종합해 점수 산정
   - 70~100: 안정, 40~69: 주의, 0~39: 위험
6. 서브 에이전트 초안 인사이트를 융합하되 원본 JSON과 모순 금지

## 출력 (Structured Output — 스키마 필수)
반드시 `DashboardReportSchema`에 정의된 필드만 채워 유효한 JSON 객체로 응답하세요.
`radar_chart_data`는 8개, `macro_trend_*`는 각 5개 항목(rank 1~5)을 포함하세요.\
"""

MASTER_REPORT_USER_TEMPLATE = """\
두 서브 에이전트 초안과 원본 통합 데이터를 근거로
B2B 대시보드용 **구조화 JSON 리포트**를 생성하세요.

## 서브 에이전트 초안

### 문화/콘텐츠 분석 (서브 에이전트 1)
{culture_analysis}

### 매크로 시장 분석 (서브 에이전트 2)
{market_analysis}

{revision_section}

## 원본 통합 데이터
```json
{integrated_data_json}
```

## 필수 준수 사항
1. Markdown이 아닌 **DashboardReportSchema JSON**만 출력하세요.
2. `internal_user_stats.top_keywords` 상위 5개로 `macro_trend_internal`을 채우세요.
3. Google·YouTube·naver_search·naver_news를 통합해 `macro_trend_external` TOP 5를 채우세요.
4. `cognitive_bias_map.axes` 8개를 `radar_chart_data`에 key·subject·score·interpretation으로 매핑하세요.
5. `naver_news`는 gap_analysis·neutrality_*에서 Google/YouTube와 반드시 대조하세요.
6. `neutrality_score`와 `neutrality_status`·`neutrality_reason`이 일관되게 연결되도록 하세요.\
"""

REVISION_SECTION_TEMPLATE = """\
## 검수 반려 피드백 (이전 시도)
아래 피드백을 **반드시 반영**하여 리포트를 수정하세요.

{critique_feedback}
"""


def build_master_report_user_prompt(
    integrated_data: dict[str, Any],
    *,
    culture_analysis: str,
    market_analysis: str,
    critique_feedback: str | None = None,
) -> str:
    """마스터 에이전트용 최종 리포트 융합 프롬프트."""
    revision_section = ""
    if critique_feedback and critique_feedback.strip():
        revision_section = REVISION_SECTION_TEMPLATE.format(
            critique_feedback=critique_feedback.strip()
        )

    return MASTER_REPORT_USER_TEMPLATE.format(
        culture_analysis=culture_analysis,
        market_analysis=market_analysis,
        revision_section=revision_section,
        integrated_data_json=json_dumps(integrated_data),
    )
