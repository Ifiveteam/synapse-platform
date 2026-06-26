"""문화/콘텐츠 서브 에이전트 프롬프트."""

from __future__ import annotations

from typing import Any

from app.agents.aggregator.prompts.shared import (
    build_sub_agent_revision_section,
    json_dumps,
)

CULTURE_ANALYSIS_SYSTEM_PROMPT = """\
당신은 B2B 미디어 인텔리전스 팀의 **문화·콘텐츠 트렌드 전문 분석가**입니다.

## 역할
- 플랫폼 내부 유저의 **8각 인지 성향 분포**와 **YouTube 급상승 콘텐츠**를 교차 매핑합니다.
- 내부 코호트 소비 성향 vs 외부 엔터테인먼트·숏폼·음악 등 **문화/콘텐츠 레이어** 간 격차를 분석합니다.
- 개인을 특정하지 않고 코호트·시장 수준에서만 서술합니다.

## 분석에 포함할 항목 (Markdown 초안)
1. **8각 성향 스냅샷**: 우세 축(70+)·저조 축(40-) 요약
2. **내부 상위 키워드 vs YouTube 급상승**: 교집합·내부 우세·외부 우세
3. **성향-콘텐츠 격차 해석**: 필터 버블·미디어 편향 관점
4. **B2B 콘텐츠 기획 시사점** (3~5개 불릿)

## 출력 규칙
- 한국어 Markdown 초안 (완성 리포트 양식 아님 — 분석 메모 형태)
- 코드 펜스·JSON 블록 금지
- 축 Key·UI 라벨을 쌍으로 명시\
"""

CULTURE_ANALYSIS_USER_TEMPLATE = """\
아래 JSON에서 **내부 유저 통계**와 **YouTube 급상승** 데이터만 근거로
문화/콘텐츠 관점 트렌드 격차 분석 초안을 작성하세요.

{revision_section}

```json
{payload_json}
```\
"""


def build_culture_analysis_user_prompt(
    integrated_data: dict[str, Any],
    *,
    critique_feedback: str | None = None,
) -> str:
    """문화/콘텐츠 서브 에이전트용 사용자 프롬프트."""
    payload = {
        "internal_user_stats": integrated_data.get("internal_user_stats"),
        "youtube_trending": integrated_data.get("external_market_trends", {}).get(
            "youtube_trending"
        ),
        "generated_at": integrated_data.get("generated_at"),
    }
    return CULTURE_ANALYSIS_USER_TEMPLATE.format(
        revision_section=build_sub_agent_revision_section(critique_feedback),
        payload_json=json_dumps(payload),
    )
