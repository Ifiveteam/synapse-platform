"""가이드 생성 프롬프트 — 심화(성향, 시청 근거) + 확장(새 도메인, 다리/전방향)."""

from __future__ import annotations

from app.agents.navigator.constants import DISPOSITION_LABELS_KO
from app.agents.navigator.sub_agent.guide.schemas import CatalogHit


def _render_deepen(
    deepen: list[str],
    gaps: dict[str, float],
    evidence: dict[str, list[CatalogHit]],
) -> str:
    if not deepen:
        return "(없음)"
    blocks: list[str] = []
    for axis in deepen:
        label = DISPOSITION_LABELS_KO.get(axis, axis)
        hits = evidence.get(axis) or []
        head = f"- {label}({axis}) · 키울 폭 {gaps.get(axis, 0)}"
        if hits:
            lines = "\n".join(f"    · {h.title} — {h.channel}" for h in hits)
            blocks.append(f"{head}\n  [실제 본 콘텐츠]\n{lines}")
        else:
            blocks.append(f"{head}\n  [관련 시청 없음 — 일반 지침]")
    return "\n".join(blocks)


def _render_expand(
    expand: list[str],
    gaps: dict[str, float],
    bridge: dict[str, list[CatalogHit]],
) -> str:
    if not expand:
        return "(없음)"
    blocks: list[str] = []
    for domain in expand:
        hits = bridge.get(domain) or []
        head = f"- {domain} · 새로 올릴 폭 {gaps.get(domain, 0)}"
        if hits:
            lines = "\n".join(f"    · {h.title} — {h.channel}" for h in hits)
            blocks.append(f"{head}\n  [이어줄 만한 기존 시청(다리)]\n{lines}")
        else:
            blocks.append(f"{head}\n  [기존 시청과 접점 없음 — 새로 시작]")
    return "\n".join(blocks)


def build_guide_prompt(
    *,
    deepen_targets: list[str],
    deepen_gaps: dict[str, float],
    evidence: dict[str, list[CatalogHit]],
    expand_domains: list[str],
    expand_gaps: dict[str, float],
    bridge_evidence: dict[str, list[CatalogHit]],
    ideal_type: str,
    reasoning: str,
) -> str:
    return f"""당신은 Synapse Navigator 에이전트입니다.
사용자가 이상향에 가까워지도록, 두 종류의 행동 가이드를 만듭니다.

[이상향 유형] {ideal_type}
[이상향 근거] {reasoning or "(없음)"}

━━ 심화(deepen) — 기존 취향을 더 깊게 (실제 시청 근거 활용) ━━
{_render_deepen(deepen_targets, deepen_gaps, evidence)}

━━ 확장(expand) — 새 도메인으로 넓히기 (안 보던 영역) ━━
{_render_expand(expand_domains, expand_gaps, bridge_evidence)}

규칙:
- 각 스텝의 `kind`: 심화 항목은 "deepen", 확장 항목은 "expand".
- `axis`: 심화면 위 성향 key(immersion 등), 확장이면 도메인명(지식·교육 등) 그대로.
- **심화 스텝**: '실제 본 콘텐츠'가 있으면 그 채널/영상을 언급하며 더 깊게 보는 행동으로.
- **확장 스텝**: '다리'가 있으면 그 시청을 발판으로 자연스럽게 새 도메인으로 이어주고,
  없으면 그 도메인을 부담 없이 시작하는 진입 방법(짧은 입문부터)으로.
- title/detail 한국어. summary 2~3문장. 심화·확장 타깃을 모두 커버, 스텝 3~6개.
- detail 은 콘텐츠 소비 습관을 바꾸는 실천 가능한 행동으로 씁니다."""
