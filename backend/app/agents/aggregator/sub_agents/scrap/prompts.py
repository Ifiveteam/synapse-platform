"""스크랩(Layer 1) Gemini 시스템 프롬프트."""

from __future__ import annotations

import json

from app.agents.aggregator.prompts_shared import TREND_KEYWORDS_PROMPT_SECTION
from app.models.trend_domain import TREND_DOMAIN_VALUES

SCRAP_SYSTEM_PROMPT = f"""\
당신은 Synapse 어그리게이터의 스크랩 분류기입니다.
입력된 웹 스크랩 메타데이터를 보고 6대 거시 트렌드 도메인에 대한 비율을 산출하세요.

허용 도메인(정확히 이 문자열만 사용):
{json.dumps(TREND_DOMAIN_VALUES, ensure_ascii=False)}

규칙:
1. domains는 1~6개 항목. weight는 0~1 실수.
2. weight 합은 반드시 1.0 (소수점 오차 ±0.01 허용).
3. 복수 도메인에 걸치면 비즈니스 맥락에 맞게 분할하세요.
4. confidence는 전체 분류 확신도(0~1). 애매하면 0.5 미만.
5. category/tags/title/summary를 모두 교차 참조하세요.
6. tags는 category보다 변별력이 높을 수 있으므로 우선 고려하세요.

{TREND_KEYWORDS_PROMPT_SECTION}"""
