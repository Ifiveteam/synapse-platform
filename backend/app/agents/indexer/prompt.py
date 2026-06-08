import os

from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

CATEGORY_LIST = [
    "게임",
    "음악",
    "영화/드라마",
    "스포츠",
    "뉴스/정치",
    "교육/강의",
    "요리/음식",
    "여행",
    "패션/뷰티",
    "기술/IT",
    "경제/금융",
    "예능/오락",
    "동물",
    "건강/운동",
    "기타",
]

SYSTEM_PROMPT = """당신은 YouTube 영상 제목을 보고 카테고리를 분류하는 전문가입니다.
아래 카테고리 중 하나만 선택해서 JSON 배열로 응답하세요.
카테고리: {categories}

응답 형식 (JSON만, 설명 없이):
["카테고리1", "카테고리2", ...]
""".format(categories=", ".join(CATEGORY_LIST))


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

    import json
    import re

    text = response.text.strip()
    text = re.sub(r"```json|```", "", text).strip()
    result = json.loads(text)
    return result
