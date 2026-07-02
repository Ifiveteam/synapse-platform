from __future__ import annotations

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.profiler.sub_agent.video_summary.state import CatalogInput
from app.schemas.profiler.llm.video import INTENTS, TONES, VALUES

_TONE_LIST = ", ".join(TONES)
_INTENT_LIST = ", ".join(INTENTS)
_VALUE_LIST = ", ".join(VALUES)

SYSTEM_PROMPT = f"""너는 유튜브 시청 성향 분석을 위한 영상 의미 분석가다.
주어진 메타데이터(제목/채널/설명/태그/카테고리)만 근거로 아래를 한국어로 산출한다.

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
- 메타데이터만으로 보수적으로 추론하고, 구체적 사실은 지어내지 않는다.
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
    return "\n".join(parts)


def build_messages(catalog: CatalogInput) -> list[BaseMessage]:
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_format_video(catalog)),
    ]


def has_min_content(catalog: CatalogInput) -> bool:
    return bool(catalog.get("title") or catalog.get("description"))


# ── 배치 프롬프트 (영상 N개를 한 번에) ──────────────────────────────
_BATCH_DESC_MAX = 150  # 배치에선 설명을 짧게 잘라 토큰 관리

BATCH_SYSTEM_PROMPT = f"""너는 유튜브 시청 성향 분석가다.
아래에 [번호]로 매겨진 여러 영상의 메타데이터(제목/채널/설명/태그/카테고리)가 주어진다.
**각 영상마다** 아래를 한국어로 산출해, 반드시 그 영상의 [번호]를 index로 넣어 items 리스트로 반환한다.

1. summary_kr: 유저 성향 추론용 시맨틱 브리프 (3~5문장, 200~400자)
   (1)주제·도메인 (2)시청 동기 (3)인지·소비 방식 (4)감정·톤 맥락 (5)가치·태도 순.
   제목·채널명만 반복하지 말고, 라벨(tones/intents/value_signals)과 같은 단어도 반복하지 않는다.
2. tones: 아래 톤 어휘에서 가장 맞는 3개 [{_TONE_LIST}]
3. intents: 아래 의도 어휘에서 가장 맞는 3개 [{_INTENT_LIST}]
4. value_signals: 아래 가치 어휘에서 가장 맞는 3개 [{_VALUE_LIST}]

규칙:
- 라벨은 반드시 위 목록 단어만 사용, 각각 서로 다른 3개. 목록에 없는 단어는 만들지 않는다.
- **입력된 영상 개수만큼 items를 반환**하고, 각 item의 index는 해당 [번호]와 정확히 일치시킨다.
- 메타데이터만으로 보수적으로 추론하고 사실을 지어내지 않는다. 임상·정신의학적 진단은 하지 않는다."""


def _format_video_batch(catalog: CatalogInput) -> str:
    parts: list[str] = []
    if catalog.get("title"):
        parts.append(f"제목: {catalog['title']}")
    parts.append(f"채널: {catalog.get('channel') or '미상'}")
    if catalog.get("youtube_category_id"):
        parts.append(f"카테고리ID: {catalog['youtube_category_id']}")
    tags = catalog.get("tags")
    if tags:
        joined = (
            ", ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags)
        )
        parts.append(f"태그: {joined}")
    desc = catalog.get("description")
    if desc:
        parts.append(f"설명: {desc[:_BATCH_DESC_MAX]}")
    return "\n".join(parts)


def build_batch_messages(catalogs: list[CatalogInput]) -> list[BaseMessage]:
    """영상 여러 개를 [번호]로 나열한 배치 프롬프트."""
    blocks = [f"[{i}]\n{_format_video_batch(c)}" for i, c in enumerate(catalogs)]
    return [
        SystemMessage(content=BATCH_SYSTEM_PROMPT),
        HumanMessage(content="\n\n".join(blocks)),
    ]
