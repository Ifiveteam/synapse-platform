import json
import os
import re
import time

from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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
아래 카테고리 중 가장 적합한 하나만 선택해서 JSON 배열로 응답하세요.
절대 "기타"를 선택하지 말고 가장 가까운 카테고리를 선택하세요.

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

응답 형식 (JSON만, 설명 없이):
["카테고리1", "카테고리2", ...]
"""

KEYWORD_PROMPT = """당신은 YouTube 영상 제목에서 핵심 키워드를 추출하는 전문가입니다.
각 영상 제목에서 핵심 키워드를 반드시 3~5개 추출해서 JSON 형식으로 응답하세요.
키워드가 부족하면 관련 주제어를 추가하세요.
신조어, 인명, 브랜드명, 주제어 모두 포함하세요.

응답 형식 (JSON만, 설명 없이):
[["키워드1", "키워드2", "키워드3"], ["키워드1", "키워드2", "키워드3"], ...]
"""



def classify_batch(titles: list[str]) -> list[str]:
    """영상 제목 배치 분류"""
    prompt = SYSTEM_PROMPT + "\n\n영상 제목 목록:\n"
    for i, title in enumerate(titles):
        prompt += f"{i + 1}. {title}\n"

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            text = response.choices[0].message.content.strip()
            text = re.sub(r"```json|```", "", text).strip()
            result = json.loads(text)
            if len(result) != len(titles):
                result = result + ["기타"] * (len(titles) - len(result))
            return result
        except Exception as e:
            print(f"분류 에러 (시도 {attempt + 1}/3): {e}")
            time.sleep(3)

    return ["기타"] * len(titles)


def extract_keywords_batch(titles: list[str]) -> list[list[str]]:
    """영상 제목 배치 키워드 추출"""
    prompt = KEYWORD_PROMPT + "\n\n영상 제목 목록:\n"
    for i, title in enumerate(titles):
        prompt += f"{i + 1}. {title}\n"

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            text = response.choices[0].message.content.strip()
            text = re.sub(r"```json|```", "", text).strip()
            result = json.loads(text)
            if len(result) != len(titles):
                result = result + [[]] * (len(titles) - len(result))
            return result
        except Exception as e:
            print(f"키워드 에러 (시도 {attempt + 1}/3): {e}")
            time.sleep(3)

    return [[] for _ in titles]