"""프로파일 초상(portrait) — 관심사·소비스타일(결정적) + 성향·키워드(LLM 1회).

catalog 원본(카테고리·채널·태그·포맷)만 사용. 영상별 요약(video_summary) 미사용.
숫자(watch_count·length)는 결정적 소비스타일로, LLM엔 텍스트 신호만.
업로드/분석 시 산출해 user_profile_history.portrait(JSONB)에 저장.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from pydantic import BaseModel, Field

from app.agents.shared.analysis_window import WATCH_CATALOG_WINDOW_DAYS
from app.repositories.profiler_repository import fetch_catalog_signal_rows

# 15 YouTube 카테고리 → 9 도메인 (누락 없이 전부 매핑)
_DOMAIN_MAP = {
    "17": "스포츠",
    "20": "게임",
    "10": "음악",
    "24": "예능",
    "23": "예능",
    "22": "인물·일상",
    "1": "영화·애니",
    "25": "뉴스·시사",
    "29": "뉴스·시사",
    "27": "지식·교육",
    "28": "지식·교육",
    "26": "라이프·취미",
    "19": "라이프·취미",
    "15": "라이프·취미",
    "2": "라이프·취미",
}
_DOMAINS = [
    "스포츠",
    "게임",
    "음악",
    "예능",
    "인물·일상",
    "영화·애니",
    "뉴스·시사",
    "지식·교육",
    "라이프·취미",
]
_CAT_LABEL = {
    "1": "영화/애니",
    "2": "자동차",
    "10": "음악",
    "15": "애완동물",
    "17": "스포츠",
    "19": "여행",
    "20": "게임",
    "22": "인물/블로그",
    "23": "코미디",
    "24": "엔터",
    "25": "뉴스/정치",
    "26": "노하우/스타일",
    "27": "교육",
    "28": "과학/기술",
    "29": "사회운동",
}

_TOP_CATEGORIES = 7
_TOP_CHANNELS = 20
_TOP_TAGS = 50
_CHANNEL_KW = 4

# 성향 6축 (LLM 영문키 → 표시 한글, 명확한 단어)
_AXIS_KO = [
    ("몰입도", "immersion"),
    ("탐험성", "exploration"),
    ("팬심", "fandom"),
    ("트렌드민감", "trend"),
    ("정보추구", "info"),
    ("감성지향", "emotion"),
]


class DispositionLLM(BaseModel):
    """LLM 출력 — 성향 6축(0~100) + 키워드 + 별칭."""

    immersion: int = Field(
        ..., ge=0, le=100, description="몰입도: 깊게 파고듦(높음) vs 얕게"
    )
    exploration: int = Field(
        ..., ge=0, le=100, description="탐험성: 다양하게(높음) vs 소수 집중"
    )
    fandom: int = Field(
        ..., ge=0, le=100, description="팬덤열정: 특정 인물/팀/그룹 몰입"
    )
    trend: int = Field(..., ge=0, le=100, description="트렌드민감도: 유행·숏폼 즉시성")
    info: int = Field(
        ..., ge=0, le=100, description="정보지향: 학습/전문(높음) vs 순수오락"
    )
    emotion: int = Field(..., ge=0, le=100, description="감성지향: 정서·위로 몰입")
    keywords: list[str] = Field(
        ..., description="이 사람을 나타내는 키워드 5~7개 (주제 앵커 + 소비성향)"
    )
    persona_label: str = Field(..., description="한 줄 별칭 (형용사+명사류)")
    reasoning: str = Field(..., description="근거 2~3문장")


def _norm_entropy(counts: list[int]) -> float:
    """정규화 섀넌 엔트로피 0~1 (분포가 고를수록 1)."""
    total = sum(counts)
    if total <= 0:
        return 0.0
    probs = [c / total for c in counts if c > 0]
    if len(probs) <= 1:
        return 0.0
    h = -sum(p * math.log(p) for p in probs)
    return h / math.log(len(probs))


def interest_radar(rows) -> list[dict[str, Any]]:
    c: Counter = Counter()
    for r in rows:
        c[_DOMAIN_MAP.get(str(r.youtube_category_id), "라이프·취미")] += 1
    n = len(rows) or 1
    return [{"axis": d, "value": round(100 * c.get(d, 0) / n, 1)} for d in _DOMAINS]


def consumption_style(rows) -> list[dict[str, Any]]:
    n = len(rows) or 1
    shorts = sum(1 for r in rows if r.is_shorts)
    chans: Counter = Counter(r.channel for r in rows if r.channel)
    cats: Counter = Counter(str(r.youtube_category_id) for r in rows)
    top_chan = chans.most_common(1)[0][1] if chans else 0
    repeat = sum(1 for r in rows if int(r.watch_count or 1) > 1)
    return [
        {"label": "숏폼 비율", "value": round(100 * shorts / n, 1)},
        {"label": "채널 집중도", "value": round(100 * top_chan / n, 1)},
        {
            "label": "관심 다양성",
            "value": round(100 * _norm_entropy(list(cats.values())), 1),
        },
        {"label": "반복 시청", "value": round(100 * repeat / n, 1)},
    ]


def channel_keywords(rows) -> dict[str, list[str]]:
    """상위 채널별 키워드 — 태그 우선, 없으면 대표 제목 폴백."""
    tags_by: dict[str, Counter] = defaultdict(Counter)
    titles_by: dict[str, list[str]] = defaultdict(list)
    count_by: Counter = Counter()
    for r in rows:
        ch = r.channel
        if not ch:
            continue
        count_by[ch] += 1
        for t in r.tags or []:
            if isinstance(t, str) and t.strip():
                tags_by[ch][t.strip()] += 1
        if r.title and len(titles_by[ch]) < 2:
            titles_by[ch].append(r.title)
    out: dict[str, list[str]] = {}
    for ch, _ in count_by.most_common(_TOP_CHANNELS):
        kws = [t for t, _ in tags_by[ch].most_common(_CHANNEL_KW)]
        if not kws:
            kws = titles_by[ch][:2]  # 태그 없으면 대표 제목
        out[ch] = kws
    return out


def _build_prompt(rows) -> str:
    n = len(rows) or 1
    shorts = sum(1 for r in rows if r.is_shorts)
    cats: Counter = Counter(
        _CAT_LABEL.get(str(r.youtube_category_id), str(r.youtube_category_id))
        for r in rows
    )
    tags: Counter = Counter()
    for r in rows:
        for t in r.tags or []:
            if isinstance(t, str) and t.strip():
                tags[t.strip()] += 1
    ch_lines = "; ".join(
        f"{ch}[{', '.join(kw)}]" for ch, kw in channel_keywords(rows).items()
    )
    return (
        f"총 시청 {len(rows)}개, 숏폼비율 {round(shorts / n, 2)}\n"
        f"상위 카테고리: "
        + ", ".join(f"{c}({v})" for c, v in cats.most_common(_TOP_CATEGORIES))
        + f"\n채널별 키워드: {ch_lines}\n"
        f"상위 태그: " + ", ".join(t for t, _ in tags.most_common(_TOP_TAGS))
    )


_SYS = """너는 유튜브 시청 데이터로 소비 성향을 산출하는 분석가다.
주어진 카테고리·채널별 키워드·태그·숏폼비율을 근거로 다음을 출력한다.

1) 성향 6축을 0~100으로 매긴다:
   immersion(몰입), exploration(탐험), fandom(팬덤), trend(트렌드), info(정보지향), emotion(감성)

   [점수 규칙 — 매우 중요. 다 높게 주지 마라]
   - **0~100 전 구간을 실제로 쓴다.** 낮은 점수는 나쁜 게 아니라 '그 성향이 약하다'는 정보일 뿐이다.
   - 대부분의 사람은 **1~2개 축만 뚜렷이 높고(70+), 2~3개는 중간(40~60), 나머지는 낮다(30 이하).**
     6축을 전부 60 이상으로 주는 것은 **잘못된 분석**이다.
   - 근거(태그·채널·카테고리·숏폼비율)에서 **분명히 드러나는 축만 높게** 준다.
     근거가 약하거나 없는 축은 **과감히 낮게(30 이하)** 준다. '혹시 몰라서 중간'은 금지.
   - 상충하는 축은 둘 다 높을 수 없다: info(학습·전문 지향) ↔ 순수 오락/트렌드 소비,
     exploration(다양) ↔ fandom(소수 집중). 실제 비중대로 한쪽을 확실히 낮춘다.
   - 결과적으로 **최고 축과 최저 축의 차이가 최소 40점** 이상 벌어져, 사람마다 스파이더
     모양이 확연히 다르게 나오도록 한다.

2) 이 사람을 직관적으로 나타내는 키워드 5~7개 (주제 앵커 3~4 + 소비성향 2~3,
   '오락/재미'처럼 뭉뚱그린 말 대신 이 사람만의 결이 드러나게)
3) 한 줄 별칭과 근거(reasoning) 2~3문장.
   [reasoning 작성 규칙 — 중요]
   - **영어 표기 금지.** 성향축은 반드시 한글로만 쓴다: 몰입도, 팬심, 탐험성,
     트렌드민감, 정보추구, 감성지향. (Fandom·Immersion·Trend 같은 영어 단어 금지)
   - **'특정 분야'·'특정 콘텐츠'처럼 뭉뚱그리지 말 것.** 실제 시청한 구체적
     주제·채널·인물을 직접 이름으로 명시한다. 카테고리보다 한 단계 더 깊게
     팀·인물·프로그램명까지 (예: 'KBO 야구'보다 '두산베어스·기아타이거즈',
     '철권 프로게이머'보다 '무릎' 처럼) 근거에 나온 고유명사를 그대로 쓴다.
   - **'당신은'·'이 시청자는'·'이 사용자는' 같은 주어 없이 바로 본론으로 시작**하는
     정중체(~합니다/~됩니다)로 쓴다 (반말·개조식·주체높임 금지).
   - 왜 어떤 축을 낮게 줬는지도 한 번 짚되, 이때도 한글 축명으로."""


async def _synthesize(rows) -> DispositionLLM:
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.agents.profiler.llm import invoke_gemini_structured

    return await invoke_gemini_structured(
        [SystemMessage(content=_SYS), HumanMessage(content=_build_prompt(rows))],
        DispositionLLM,
    )


async def build_portrait(
    session, user_id, source_ids: list[str] | None
) -> dict[str, Any]:
    """스냅샷(배치 or 전체) → portrait payload. LLM 1회."""
    rows = await fetch_catalog_signal_rows(
        session, user_id, source_ids, WATCH_CATALOG_WINDOW_DAYS
    )
    interest = interest_radar(rows)
    style = consumption_style(rows)
    if not rows:
        return {
            "persona_label": "분석할 시청 데이터가 없습니다",
            "keywords": [],
            "interest": interest,
            "disposition": [],
            "style": style,
            "reasoning": "",
        }
    llm = await _synthesize(rows)
    disposition = [{"axis": ko, "value": getattr(llm, en)} for ko, en in _AXIS_KO]
    return {
        "persona_label": llm.persona_label,
        "keywords": llm.keywords,
        "interest": interest,
        "disposition": disposition,
        "style": style,
        "reasoning": llm.reasoning,
    }
