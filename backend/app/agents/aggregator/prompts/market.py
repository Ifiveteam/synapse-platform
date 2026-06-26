"""매크로 시장 서브 에이전트 프롬프트."""

from __future__ import annotations

from typing import Any

from app.agents.aggregator.prompts.shared import (
    build_sub_agent_revision_section,
    json_dumps,
)

MARKET_ANALYSIS_SYSTEM_PROMPT = """\
당신은 B2B 미디어 인텔리전스 팀의 **매크로 시장·언론 경제 전문 분석가**입니다.

## 역할
- **Google Trends RSS**와 **네이버 뉴스 RSS 헤드라인**을 기반으로
  현재 매크로 시장 및 언론 경제 이슈를 분석합니다.
- 엔터테인먼트형 검색 트렌드 vs 시사·경제 뉴스 헤드라인의 **이중 구조**를 해석합니다.
- 광고주·미디어 기획사 의사결정자 관점의 거시 인사이트를 제공합니다.

## 분석에 포함할 항목 (Markdown 초안)
1. **Google Trends TOP 이슈** 요약 및 주제 클러스터
2. **네이버 뉴스 헤드라인** 섹션별(정치·경제·사회·IT) 핵심 의제
3. **검색 트렌드 vs 뉴스 프레이밍 격차** 해석
4. **매크로·언론 경제 B2B 시사점** (3~5개 불릿)

## 출력 규칙
- 한국어 Markdown 초안 (완성 리포트 양식 아님 — 분석 메모 형태)
- 코드 펜스·JSON 블록 금지\
"""

MARKET_ANALYSIS_USER_TEMPLATE = """\
아래 JSON에서 **Google Trends**, **naver_search**, **naver_news** 데이터만 근거로
매크로 시장 및 언론 경제 이슈 분석 초안을 작성하세요.

{revision_section}

```json
{payload_json}
```\
"""


def build_market_analysis_user_prompt(
    integrated_data: dict[str, Any],
    *,
    critique_feedback: str | None = None,
) -> str:
    """매크로 시장 서브 에이전트용 사용자 프롬프트."""
    external = integrated_data.get("external_market_trends", {})
    payload = {
        "google_trends": external.get("google_trends"),
        "naver_search": external.get("naver_search"),
        "naver_news": external.get("naver_news"),
        "generated_at": integrated_data.get("generated_at"),
    }
    return MARKET_ANALYSIS_USER_TEMPLATE.format(
        revision_section=build_sub_agent_revision_section(critique_feedback),
        payload_json=json_dumps(payload),
    )
