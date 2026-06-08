import json
import os
import re

from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

CATEGORY_LIST = [
    "intellectual_curiosity",
    "self_improvement",
    "social_awareness",
    "depth_immersion",
    "practical_orientation",
    "emotional_comfort",
    "creative_expression",
    "entertainment_release",
]

CATEGORY_LABELS = {
    "intellectual_curiosity": "지적 호기심",
    "self_improvement": "자기계발",
    "social_awareness": "사회·시선",
    "depth_immersion": "깊이·몰입",
    "practical_orientation": "실용 지향",
    "emotional_comfort": "정서·위로",
    "creative_expression": "창의·표현",
    "entertainment_release": "오락·해방",
}

SYSTEM_PROMPT = """당신은 YouTube 영상 제목을 보고 카테고리를 분류하는 전문가입니다.
아래 카테고리 key 중 하나만 선택해서 JSON 배열로 응답하세요.

카테고리:
- intellectual_curiosity: 지적 호기심 (새 지식, 낯선 주제 탐색)
- self_improvement: 자기계발 (습관, 목표, 생산성)
- social_awareness: 사회·시선 (뉴스, 시사, 토크, 다큐)
- depth_immersion: 깊이·몰입 (장편, 한 주제 깊게)
- practical_orientation: 실용 지향 (튜토리얼, How-to, 문제 해결)
- emotional_comfort: 정서·위로 (힐링, ASMR, 음악, 감성)
- creative_expression: 창의·표현 (DIY, 메이킹, 창작, 예술)
- entertainment_release: 오락·해방 (예능, 게임, 스포츠, 밈)

응답 형식 (JSON만, 설명 없이):
["key1", "key2", ...]
"""


def classify_batch(titles: list[str]) -> list[str]:
    """영상 제목 배치 분류"""
    prompt = SYSTEM_PROMPT + "\n\n영상 제목 목록:\n"
    for i, title in enumerate(titles):
        prompt += f"{i + 1}. {title}\n"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
        ),
    )

    text = response.text.strip()
    text = re.sub(r"```json|```", "", text).strip()
    result = json.loads(text)
    return result
