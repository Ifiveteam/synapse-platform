"""가이드 생성 프롬프트 (그라운딩 + 폴백)."""

from __future__ import annotations

from app.agents.navigator.sub_agent.guide.store import CatalogHit
from app.agents.profiler.axis_labels import SCORE_LABELS_KO


def _render_gaps(weak_axes: list[str], gap_by_axis: dict[str, float]) -> str:
    return "\n".join(
        f"- {SCORE_LABELS_KO.get(a, a)}({a}): gap {gap_by_axis.get(a, 0)}"
        for a in weak_axes
    )


def _render_evidence(
    weak_axes: list[str], evidence: dict[str, list[CatalogHit]]
) -> str:
    blocks: list[str] = []
    for axis in weak_axes:
        label = SCORE_LABELS_KO.get(axis, axis)
        hits = evidence.get(axis) or []
        if not hits:
            blocks.append(f"[{label}({axis})] 관련 시청 영상 없음")
            continue
        lines = "\n".join(f"  - {h.title} · {h.channel}" for h in hits)
        blocks.append(f"[{label}({axis})] 관련 시청 영상:\n{lines}")
    return "\n".join(blocks)


_RULES = """규칙:
- step.axis 는 위 약한 축 key 중 하나여야 하며, 약한 축을 모두 커버합니다.
- title/detail 은 한국어. summary 2~3문장, step 3~5개.
- detail 은 콘텐츠 소비 습관을 바꾸는 실천 가능한 행동으로 적습니다."""


def build_grounded_prompt(
    *,
    weak_axes: list[str],
    gap_by_axis: dict[str, float],
    evidence: dict[str, list[CatalogHit]],
    ideal_type: str,
    reasoning: str,
) -> str:
    return f"""당신은 Synapse Navigator 에이전트입니다.
사용자가 이상향에 가까워지도록 '실제 시청 기록에 근거한' 행동 가이드를 작성합니다.

[이상향 유형] {ideal_type}
[이상향 근거] {reasoning or "(없음)"}

[키워야 할 약한 축]
{_render_gaps(weak_axes, gap_by_axis)}

[사용자가 실제로 본 콘텐츠 근거]
{_render_evidence(weak_axes, evidence)}

위 '실제 시청 콘텐츠'를 근거로, 가능하면 실제 본 채널/영상을 언급하며
약한 축을 키우는 행동을 연결해 제시합니다 (예: 즐겨 본 X 스타일로 분석형 콘텐츠를).
{_RULES}"""


def build_fallback_prompt(
    *,
    weak_axes: list[str],
    gap_by_axis: dict[str, float],
    ideal_type: str,
    reasoning: str,
) -> str:
    return f"""당신은 Synapse Navigator 에이전트입니다.
사용자의 약한 축을 키우는 행동 가이드를 작성합니다. (시청 기록 근거가 없어 일반 지침)

[이상향 유형] {ideal_type}
[이상향 근거] {reasoning or "(없음)"}

[키워야 할 약한 축]
{_render_gaps(weak_axes, gap_by_axis)}

각 약한 축을 겨냥한 실천 가능한 콘텐츠 소비 행동을 제시합니다.
{_RULES}"""
