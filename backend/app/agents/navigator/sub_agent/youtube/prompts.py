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
    if g.sample_titles:
        titles = " / ".join(g.sample_titles[:8])
        parts.append(f"최근 시청 영상 예: {titles}")
    return "\n".join(parts) if parts else "(시청기록 데이터 없음)"


def _render_current_domains(interest: dict[str, float] | None) -> str:
    if not interest:
        return "(없음)"
    top = [
        (d, v)
        for d, v in sorted(interest.items(), key=lambda x: x[1], reverse=True)
        if v > 0
    ][:5]
    return ", ".join(f"{d} {round(v)}" for d, v in top) or "(없음)"


def build_query_prompt(
    *,
    persona_label: str,
    values13: dict[str, float],
    reasoning: str,
    ideal_type: str,
    grounding: WatchGrounding | None,
    current_interest: dict[str, float] | None = None,
    raise_domains: list[str] | None = None,
    taste_keywords: list[str] | None = None,
    broaden: bool = False,
) -> str:
    extra = (
        "\n이전 검색으로 충분한 채널을 못 찾았다. 더 폭넓고 다양한 검색어로 바꿔라."
        if broaden
        else ""
    )
    raise_line = (
        ", ".join(raise_domains or []) or "(지정 없음 — 페르소나·시청기록으로 추론)"
    )
    keyword_line = ", ".join(taste_keywords or []) or "(없음 — 대화 없이 설계된 이상향)"
    return f"""당신은 Synapse Navigator의 재생목록 큐레이터입니다.
사용자의 '이상향'과 '실제 시청 기록'을 함께 근거로, 그 사람에게 어울리는
YouTube **채널**을 찾기 위한 검색어를 만듭니다.

[이상향 페르소나] {persona_label or "(없음)"} / 유형 {ideal_type}
[이상향 설계 근거] {reasoning or "(없음)"}

[사용자 시청 기록(친숙도 근거)]
{_render_grounding(grounding)}

[현재 관심 도메인] {_render_current_domains(current_interest)}
[넓힐 목표 도메인] {raise_line}
[대화에서 뽑은 구체 관심 키워드(최우선)] {keyword_line}

[보조: 이상향 가치관·기질 13축]
{render_13axis(values13)}

**중요 — 다양성 규칙:**
- **'대화에서 뽑은 구체 관심 키워드'가 있으면 그것을 최우선 씨앗으로** 검색어를 만드세요
  (예: 'AI 개발' → "AI 개발 최신 기술 채널"). 키워드는 9개 도메인보다 세부라 더 겨냥됩니다.
- 이어서 **'넓힐 목표 도메인' 각각을 겨냥해 도메인마다 검색어를 1개씩** 만드세요(서로 다른 도메인,
  한 도메인/주제로 몰지 말 것).
- 키워드·목표 도메인이 모두 없으면 페르소나·시청기록을 근거로 **서로 다른 결의 검색어 2~3개**를 만드세요.
- 시청기록(예: 특정 스포츠 채널)에만 끌려가 전부 같은 주제가 되지 않도록 주의하세요.

각 검색어는 한국어로, 너무 좁지도 넓지도 않게 **YouTube 채널이 잘 잡히는 표현**으로.{extra}"""


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
    *,
    persona_label: str,
    reasoning: str,
    candidates: list[PlaylistItem],
    raise_domains: list[str] | None = None,
) -> str:
    listed = "\n".join(
        f"{i}. {v.title} — {v.channel}" for i, v in enumerate(candidates)
    )
    domain_line = (
        f"\n- 이상향이 **넓히려는 목표 도메인({', '.join(raise_domains)})** 쪽 영상을 우선 포함하세요."
        if raise_domains
        else ""
    )
    return f"""아래는 추천 후보 영상입니다(실재 영상).
이상향 페르소나 '{persona_label}'({reasoning[:80]})에 맞는 재생목록을 구성하세요.

[영상 후보]
{listed}

규칙:
- 페르소나에 가장 잘 맞는 영상 **최대 10개**를 골라 `picks`에 인덱스로 담으세요.{domain_line}
- **다양성**: 한 채널·한 주제에 몰지 말고 **여러 채널·도메인이 고루 섞이게** 고르세요.
  한 채널에서는 **최대 3개**까지만.
- **최신 우선**: 후보는 최신순으로 정렬돼 있습니다. 적합도가 비슷하면 **더 최근 영상**을 고르세요.
- 각 picks에 그 영상을 고른 한 줄 이유(`reason`, 한국어)를 적으세요.
- `summary`에 이 재생목록의 성격을 1~2문장으로 적으세요.
- 목록에 없는 인덱스는 만들지 마세요. video_id 같은 식별자는 출력하지 마세요."""
