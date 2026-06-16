from __future__ import annotations

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.profiler.video_summary.state import WatchInput

# Gemini 입력에 넣을 트랜스크립트 최대 길이 (토큰 폭주 방지)
_TRANSCRIPT_MAX = 4000

SYSTEM_PROMPT = """너는 유튜브 영상의 의미를 분석하는 프로파일러다.
주어진 영상 메타데이터(제목/채널/설명/자막/태그/카테고리)를 보고 아래를 한국어로 산출한다.

1. summary_kr: 영상 내용을 1~2문장으로 요약
2. tones: 영상의 톤/분위기 라벨 정확히 3개 (예: 진지함, 유머, 차분함)
3. intents: 영상의 의도 라벨 정확히 3개 (예: 정보전달, 설득, 공감)
4. value_signals: 영상이 담은 가치 신호 라벨 정확히 3개 (예: 성취, 재미, 안정)

라벨은 1~4글자 내외의 짧은 단어로, 추측이 어려우면 메타데이터에서 드러나는 일반적 성향으로 채운다.
반드시 각 항목을 정확히 3개씩 채운다."""


def _format_video(watch: WatchInput) -> str:
    parts: list[str] = []
    if watch.get("title"):
        parts.append(f"제목: {watch['title']}")
    parts.append(f"채널: {watch.get('channel') or '미상'}")
    if watch.get("category"):
        parts.append(f"카테고리: {watch['category']}")
    tags = watch.get("tags")
    if tags:
        joined = (
            ", ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags)
        )
        parts.append(f"태그: {joined}")
    if watch.get("description"):
        parts.append(f"설명: {watch['description']}")
    transcript = watch.get("transcript")
    if transcript:
        parts.append(f"자막: {transcript[:_TRANSCRIPT_MAX]}")
    return "\n".join(parts)


def build_messages(watch: WatchInput) -> list[BaseMessage]:
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_format_video(watch)),
    ]


def has_min_content(watch: WatchInput) -> bool:
    """제목/설명/자막 중 하나라도 있으면 분석 가치가 있다고 본다."""
    return bool(
        watch.get("title") or watch.get("description") or watch.get("transcript")
    )
