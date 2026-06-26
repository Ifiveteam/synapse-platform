from __future__ import annotations

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.profiler.sub_agent.video_summary.state import CatalogInput
from app.schemas.profiler.llm.video import INTENTS, TONES, VALUES

_TRANSCRIPT_MAX = 4000

_TONE_LIST = ", ".join(TONES)
_INTENT_LIST = ", ".join(INTENTS)
_VALUE_LIST = ", ".join(VALUES)

SYSTEM_PROMPT = f"""너는 유튜브 시청 성향 분석을 위한 영상 의미 분석가다.
주어진 메타데이터(제목/채널/설명/자막/태그/카테고리)만 근거로 아래를 한국어로 산출한다.

1. summary_kr: 유저 성향 추론용 시맨틱 브리프 (3~5문장, 200~400자 내외)
   유저에게 보여줄 짧은 소개가 아니다. 아래 순서를 지켜 각각 1문장씩 쓴다.
   (1) 주제·도메인 — 이 영상이 다루는 영역
   (2) 시청 동기 — 유저가 왜 이 영상을 볼지 (정보·오락·실용·위로·탐색 등)
   (3) 인지·소비 방식 — 정보 수용/비교/깊이학습/가볍게 소비 중 무엇에 가까운지
   (4) 감정·톤 맥락 — tones 라벨을 나열하지 말고, 그 분위기가 형성되는 이유
   (5) 가치·태도 — value_signals 라벨을 나열하지 말고, 드러나는 가치·태도의 근거
   제목·채널명만 반복하지 말고, tones/intents/value_signals와 같은 단어도 반복하지 않는다.

2. tones: 아래 톤 어휘에서 가장 맞는 3개만 고른다.
   [{_TONE_LIST}]
3. intents: 아래 의도 어휘에서 가장 맞는 3개만 고른다.
   [{_INTENT_LIST}]
4. value_signals: 아래 가치 어휘에서 가장 맞는 3개만 고른다.
   [{_VALUE_LIST}]

공통 규칙:
- 라벨(2~4)은 반드시 위 목록에 있는 단어만 사용하고, 각각 서로 다른 3개를 고른다.
  목록에 없는 단어는 절대 만들지 않는다.
- 자막이 없으면 메타데이터에서 보수적으로 추론하고, 구체적 사실은 지어내지 않는다.
- 임상·정신의학적 진단이나 질병 단정은 하지 않는다."""


def _format_video(catalog: CatalogInput) -> str:
    parts: list[str] = []
    if catalog.get("title"):
        parts.append(f"제목: {catalog['title']}")
    parts.append(f"채널: {catalog.get('channel') or '미상'}")
    if catalog.get("youtube_category_id"):
        parts.append(f"YouTube 카테고리 ID: {catalog['youtube_category_id']}")
    tags = catalog.get("tags")
    if tags:
        joined = (
            ", ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags)
        )
        parts.append(f"태그: {joined}")
    if catalog.get("description"):
        parts.append(f"설명: {catalog['description']}")
    transcript = catalog.get("transcript")
    if transcript:
        parts.append(f"자막: {transcript[:_TRANSCRIPT_MAX]}")
    return "\n".join(parts)


def build_messages(catalog: CatalogInput) -> list[BaseMessage]:
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_format_video(catalog)),
    ]


def has_min_content(catalog: CatalogInput) -> bool:
    return bool(
        catalog.get("title") or catalog.get("description") or catalog.get("transcript")
    )
