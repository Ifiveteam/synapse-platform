"""재생목록 서브에이전트 프롬프트 — 검색어 / 채널선택 / 큐레이션."""

from __future__ import annotations

from app.agents.navigator.prompts import render_13axis
from app.agents.navigator.schemas import PlaylistItem
from app.agents.navigator.sub_agent.youtube.schemas import ChannelRef, WatchGrounding


def _render_grounding(g: WatchGrounding | None) -> str:
    if not g:
        return "(시청기록 데이터 없음)"
    parts = []
    if g.channels:
        parts.append(f"자주 본 채널: {', '.join(g.channels[:8])}")
    if g.categories:
        parts.append(f"상위 카테고리: {', '.join(g.categories[:8])}")
    if g.sample_titles:
        titles = " / ".join(g.sample_titles[:8])
        parts.append(f"최근 시청 영상 예: {titles}")
    return "\n".join(parts) if parts else "(시청기록 데이터 없음)"


def build_query_prompt(
    *,
    persona_label: str,
    values13: dict[str, float],
    reasoning: str,
    ideal_type: str,
    grounding: WatchGrounding | None,
    broaden: bool = False,
) -> str:
    extra = (
        "\n이전 검색으로 충분한 채널을 못 찾았다. 더 폭넓고 다양한 검색어로 바꿔라."
        if broaden
        else ""
    )
    return f"""당신은 Synapse Navigator의 재생목록 큐레이터입니다.
사용자의 '이상향 페르소나'와 '실제 시청 기록'을 함께 근거로, 그 사람에게 어울리는
YouTube **채널**을 찾기 위한 검색어를 만듭니다.

[이상향 페르소나] {persona_label or "(없음)"} / 유형 {ideal_type}
[이상향 설계 근거] {reasoning or "(없음)"}

[이상향 가치관·기질 13축]
{render_13axis(values13)}

[사용자 시청 기록(친숙도 근거)]
{_render_grounding(grounding)}

이상향 방향(성장)과 시청 기록(친숙함)을 모두 반영해, **YouTube 채널 검색에 쓸
한국어 검색어 1~2개**를 만드세요. 너무 좁지도 넓지도 않게, 채널이 잘 잡히는 표현으로.{extra}"""


def build_pick_prompt(
    *, persona_label: str, reasoning: str, channels: list[ChannelRef]
) -> str:
    listed = "\n".join(
        f"{i}. {c.title} — {(c.description or '')[:60]}" for i, c in enumerate(channels)
    )
    return f"""아래는 검색으로 찾은 실재 YouTube 채널 후보입니다.
이상향 페르소나 '{persona_label}'({reasoning[:80]})에 가장 잘 맞는 채널들을 고르세요.

[채널 후보]
{listed}

페르소나에 부합하고 콘텐츠가 꾸준할 법한 채널의 **인덱스**만 고르세요(최대 10개).
실제 목록에 없는 번호는 절대 만들지 마세요."""


def build_curate_prompt(
    *, persona_label: str, reasoning: str, candidates: list[PlaylistItem]
) -> str:
    listed = "\n".join(
        f"{i}. {v.title} — {v.channel}" for i, v in enumerate(candidates)
    )
    return f"""아래는 추천 후보 영상입니다(실재 영상).
이상향 페르소나 '{persona_label}'({reasoning[:80]})에 맞는 재생목록을 구성하세요.

[영상 후보]
{listed}

규칙:
- 페르소나에 가장 잘 맞는 영상 **최대 10개**를 골라 `picks`에 인덱스로 담으세요.
- 각 picks에 그 영상을 고른 한 줄 이유(`reason`, 한국어)를 적으세요.
- `summary`에 이 재생목록의 성격을 1~2문장으로 적으세요.
- 목록에 없는 인덱스는 만들지 마세요. video_id 같은 식별자는 출력하지 마세요."""
