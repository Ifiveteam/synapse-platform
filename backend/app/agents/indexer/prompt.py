import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CATEGORY_LIST = [
    "게임",
    "과학기술",
    "교육",
    "노하우/스타일",
    "뉴스/정치",
    "비영리/사회운동",
    "스포츠",
    "애완동물/동물",
    "엔터테인먼트",
    "여행/이벤트",
    "영화/애니메이션",
    "음악",
    "인물/블로그",
    "자동차/교통",
    "코미디",
]

DEFAULT_CATEGORY = "인물/블로그"

# 이전 taxonomy / GPT 오분류 → YouTube 15개로 매핑
LEGACY_CATEGORY_MAP: dict[str, str] = {
    "기타": "인물/블로그",
    "영화/드라마": "영화/애니메이션",
    "교육/강의": "교육",
    "요리/음식": "노하우/스타일",
    "여행": "여행/이벤트",
    "패션/뷰티": "노하우/스타일",
    "기술/IT": "과학기술",
    "경제/금융": "뉴스/정치",
    "예능/오락": "엔터테인먼트",
    "동물": "애완동물/동물",
    "건강/운동": "노하우/스타일",
    "IT": "과학기술",
    "테크": "과학기술",
    "먹방": "노하우/스타일",
    "브이로그": "인물/블로그",
}

SYSTEM_PROMPT = """당신은 YouTube 영상 제목과 설명을 보고 카테고리를 분류하는 전문가입니다.
아래 YouTube 공식 카테고리 15개 중 가장 적합한 하나만 선택하세요. 목록 밖의 이름은 사용하지 마세요.

카테고리:
- 게임: 게임 플레이, 공략, 리뷰, e스포츠
- 과학기술: IT, 프로그래밍, 과학, 기술 리뷰, AI
- 교육: 강의, 튜토리얼, 학습, 지식 콘텐츠
- 노하우/스타일: 요리, 패션, 뷰티, DIY, 생활 팁, 건강·운동
- 뉴스/정치: 시사, 뉴스, 정치, 사회 이슈
- 비영리/사회운동: 캠페인, 기부, 사회운동, NGO
- 스포츠: 축구, 야구, 농구, 운동 경기, e스포츠 외 스포츠
- 애완동물/동물: 반려동물, 동물, 자연
- 엔터테인먼트: 예능, 버라이어티, 쇼, 연예
- 여행/이벤트: 여행, 브이로그, 관광, 행사
- 영화/애니메이션: 영화, 드라마, 애니메이션, 영상 리뷰
- 음악: 뮤직비디오, 노래, 커버, 악기
- 인물/블로그: 일상 브이로그, 개인 이야기, 분류 애매한 일반 콘텐츠
- 자동차/교통: 자동차, 바이크, 교통, 드라이브
- 코미디: 코미디, 유머, 웃긴 영상, 밈

응답 형식 (JSON 오브젝트, 설명 없이):
{"results": ["카테고리1", "카테고리2", ...]}
"""


def normalize_category(value: str | None) -> str:
    """반환값을 YouTube 공식 15개 카테고리 중 하나로 강제."""
    if not value or not str(value).strip():
        return DEFAULT_CATEGORY

    cat = str(value).strip()
    if cat in CATEGORY_LIST:
        return cat
    if cat in LEGACY_CATEGORY_MAP:
        return LEGACY_CATEGORY_MAP[cat]

    lowered = cat.lower()
    for valid in CATEGORY_LIST:
        if valid.lower() == lowered:
            return valid
        if valid in cat or cat in valid:
            return valid

    for legacy, mapped in LEGACY_CATEGORY_MAP.items():
        if legacy in cat or cat in legacy:
            return mapped

    return DEFAULT_CATEGORY


def _parse_classify_results(parsed: object, expected: int) -> list[str]:
    if isinstance(parsed, dict):
        raw = parsed.get("results") or next(iter(parsed.values()), [])
    elif isinstance(parsed, list):
        raw = parsed
    else:
        raw = []

    result: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            result.append(normalize_category(item.get("category")))
        elif isinstance(item, list) and item:
            result.append(normalize_category(str(item[0])))
        else:
            result.append(normalize_category(str(item)))
    return result[:expected]


def _classify_batch_once(texts: list[str]) -> list[str]:
    prompt = SYSTEM_PROMPT + "\n\n영상 목록 (제목 + 설명):\n"
    for i, text in enumerate(texts):
        prompt += f"{i + 1}. {text}\n"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=max(600, len(texts) * 20),
        timeout=60,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()
    parsed = json.loads(raw)
    return _parse_classify_results(parsed, len(texts))


def classify_one(text: str) -> str:
    """단건 분류 — 배치 실패 시 폴백."""
    for attempt in range(3):
        try:
            results = _classify_batch_once([text])
            if results:
                return normalize_category(results[0])
        except Exception as e:
            print(f"단건 분류 에러 (시도 {attempt + 1}/3): {e}")
            time.sleep(1)
    return DEFAULT_CATEGORY


KEYWORD_PROMPT = """당신은 YouTube 영상 제목과 설명에서 핵심 키워드를 추출하는 전문가입니다.
각 영상에서 핵심 키워드를 반드시 3~5개 추출해서 JSON 형식으로 응답하세요.
키워드가 부족하면 관련 주제어를 추가하세요.
신조어, 인명, 브랜드명, 주제어 모두 포함하세요.

응답 형식 (JSON만, 설명 없이):
[["키워드1", "키워드2", "키워드3"], ["키워드1", "키워드2", "키워드3"], ...]
"""


def classify_batch(texts: list[str]) -> list[str]:
    """영상 배치 분류 (제목 + description). 항상 len(texts)개·유효 카테고리 보장."""
    if not texts:
        return []

    for attempt in range(3):
        try:
            result = _classify_batch_once(texts)
            if len(result) < len(texts):
                print(f"[분류] 배치 결과 부족 ({len(result)}/{len(texts)}) — 단건 보완")
                for idx in range(len(result), len(texts)):
                    result.append(classify_one(texts[idx]))
            elif len(result) > len(texts):
                result = result[: len(texts)]
            return [normalize_category(cat) for cat in result]
        except Exception as e:
            print(f"분류 에러 (시도 {attempt + 1}/3): {e}")
            time.sleep(1)

    print(f"[분류] 배치 전체 실패 — {len(texts)}건 단건 재시도")
    return [classify_one(text) for text in texts]


CLASSIFY_AND_KEYWORDS_PROMPT = """당신은 YouTube 영상 제목과 설명을 보고 카테고리 분류와 핵심 키워드를 동시에 추출하는 전문가입니다.

카테고리는 아래 YouTube 공식 15개 중 하나만 선택하세요 (목록 밖 이름 금지):
게임, 과학기술, 교육, 노하우/스타일, 뉴스/정치, 비영리/사회운동, 스포츠, 애완동물/동물, 엔터테인먼트, 여행/이벤트, 영화/애니메이션, 음악, 인물/블로그, 자동차/교통, 코미디

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
                cat = normalize_category(r.get("category"))
                kws = r.get("keywords", [])
                normalized.append({"category": cat, "keywords": kws[:5]})
            if len(normalized) != len(texts):
                normalized += [{"category": DEFAULT_CATEGORY, "keywords": []}] * (
                    len(texts) - len(normalized)
                )
            return normalized
        except Exception as e:
            print(f"분류+키워드 에러 (시도 {attempt + 1}/3): {e}")
            time.sleep(3)

    return [{"category": DEFAULT_CATEGORY, "keywords": []} for _ in texts]


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
