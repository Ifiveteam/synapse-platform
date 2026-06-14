import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

SYSTEM_PROMPT = """당신은 YouTube 영상 제목과 설명을 보고 카테고리를 분류하는 전문가입니다.
아래 카테고리 중 가장 적합한 하나만 선택하세요. 절대 "기타"를 선택하지 말고 가장 가까운 카테고리를 선택하세요.

카테고리:
- 게임: 게임 플레이, 공략, 리뷰, e스포츠
- 음악: 뮤직비디오, 노래, 커버, 악기
- 영화/드라마: 영화, 드라마, 애니메이션, 리뷰
- 스포츠: 축구, 야구, 농구, 운동 경기
- 뉴스/정치: 시사, 뉴스, 정치, 사회이슈
- 교육/강의: 공부, 강의, 튜토리얼, 지식
- 요리/음식: 요리, 먹방, 레시피, 맛집
- 여행: 여행, 브이로그, 관광
- 패션/뷰티: 패션, 메이크업, 스킨케어
- 기술/IT: 테크, 프로그래밍, 리뷰, AI
- 경제/금융: 주식, 부동산, 재테크, 경제
- 예능/오락: 예능, 버라이어티, 웃긴영상, 밈
- 동물: 동물, 반려동물, 고양이, 강아지
- 건강/운동: 헬스, 다이어트, 건강, 요가
- 기타: 위 카테고리에 전혀 해당하지 않는 경우만

응답 형식 (JSON 오브젝트, 설명 없이):
{"results": ["카테고리1", "카테고리2", ...]}
"""

KEYWORD_PROMPT = """당신은 YouTube 영상 제목과 설명에서 핵심 키워드를 추출하는 전문가입니다.
각 영상에서 핵심 키워드를 반드시 3~5개 추출해서 JSON 형식으로 응답하세요.
키워드가 부족하면 관련 주제어를 추가하세요.
신조어, 인명, 브랜드명, 주제어 모두 포함하세요.

응답 형식 (JSON만, 설명 없이):
[["키워드1", "키워드2", "키워드3"], ["키워드1", "키워드2", "키워드3"], ...]
"""


def classify_batch(texts: list[str]) -> list[str]:
    """영상 배치 분류 (제목 + description)"""
    prompt = SYSTEM_PROMPT + "\n\n영상 목록 (제목 + 설명):\n"
    for i, text in enumerate(texts):
        prompt += f"{i + 1}. {text}\n"

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=600,
                timeout=30,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content.strip()
            parsed = json.loads(raw)
            result = parsed.get("results") or list(parsed.values())[0]
            result = [r[0] if isinstance(r, list) else str(r) for r in result]
            if len(result) != len(texts):
                result = result + ["기타"] * (len(texts) - len(result))
            return result
        except Exception as e:
            print(f"분류 에러 (시도 {attempt + 1}/3): {e}")
            time.sleep(1)

    return ["기타"] * len(texts)


CLASSIFY_AND_KEYWORDS_PROMPT = """당신은 YouTube 영상 제목과 설명을 보고 카테고리 분류와 핵심 키워드를 동시에 추출하는 전문가입니다.

카테고리는 아래 15개 중 하나만 선택하세요 (절대 "기타" 선택 금지):
게임, 음악, 영화/드라마, 스포츠, 뉴스/정치, 교육/강의, 요리/음식, 여행, 패션/뷰티, 기술/IT, 경제/금융, 예능/오락, 동물, 건강/운동, 기타

키워드는 반드시 3~5개 추출하세요. 신조어, 인명, 브랜드명, 주제어 모두 포함하세요.

응답 형식 (JSON만, 설명 없이):
{"results": [{"category": "카테고리", "keywords": ["키워드1", "키워드2", "키워드3"]}, ...]}
"""


def classify_and_keywords_batch(texts: list[str]) -> list[dict]:
    """분류 + 키워드 동시 추출 (GPT 호출 1번으로 둘 다)"""
    prompt = CLASSIFY_AND_KEYWORDS_PROMPT + "\n\n영상 목록:\n"
    for i, text in enumerate(texts):
        prompt += f"{i + 1}. {text}\n"

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content.strip()
            parsed = json.loads(text)
            results = parsed.get(
                "results",
                parsed if isinstance(parsed, list) else list(parsed.values())[0],
            )
            normalized = []
            for r in results:
                cat = r.get("category", "기타")
                kws = r.get("keywords", [])
                cat = cat[0] if isinstance(cat, list) else str(cat)
                normalized.append({"category": cat, "keywords": kws[:5]})
            if len(normalized) != len(texts):
                normalized += [{"category": "기타", "keywords": []}] * (
                    len(texts) - len(normalized)
                )
            return normalized
        except Exception as e:
            print(f"분류+키워드 에러 (시도 {attempt + 1}/3): {e}")
            time.sleep(3)

    return [{"category": "기타", "keywords": []} for _ in texts]


def extract_keywords_batch(texts: list[str]) -> list[list[str]]:
    """영상 배치 키워드 추출 (제목 + description)"""
    prompt = KEYWORD_PROMPT + "\n\n영상 목록 (제목 + 설명):\n"
    for i, text in enumerate(texts):
        prompt += f"{i + 1}. {text}\n"

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content.strip()
            parsed = json.loads(text)
            result = parsed if isinstance(parsed, list) else list(parsed.values())[0]
            if len(result) != len(texts):
                result = result + [[]] * (len(texts) - len(result))
            return result
        except Exception as e:
            print(f"키워드 에러 (시도 {attempt + 1}/3): {e}")
            time.sleep(3)

    return [[] for _ in texts]
