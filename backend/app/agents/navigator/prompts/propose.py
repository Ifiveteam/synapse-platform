"""이상향 자동 제안 프롬프트 (반대 / 강점심화 / 균형).

주 신호 = portrait(성향 6축 + 관심 도메인). 21축은 보조 맥락.
목표는 LLM이 직접 산출한다(규칙 없음). 반대형은 극단 반전으로 확실히 벌린다.
"""

from __future__ import annotations

from app.agents.navigator.constants import INTEREST_DOMAINS
from app.agents.navigator.prompts import (
    render_13axis,
    render_disposition,
    render_domains,
    render_interests,
)
from app.agents.navigator.schemas import IdealType

_OUTPUT_GUIDE = f"""출력 규칙:
1) **target_disposition** — 이상향의 목표 성향 6축(immersion 몰입도, exploration 탐험성,
   fandom 팬심, trend 트렌드민감, info 정보추구, emotion 감성지향)을 0~100으로.
2) **target_interest** — 아래 9개 관심 도메인 각각의 목표값(0~100). 도메인명은 그대로 사용:
   {", ".join(INTEREST_DOMAINS)}
3) **가치관 10축 + 기질 3축**(self_direction 등)도 함께 채운다(내부 파생용, 화면엔 안 나옴).
4) persona_label(5~12자, 과장 없이) + reasoning(3~5문장).
성향·도메인은 반드시 [현재]와 대비해 위 유형 의도만큼 **뚜렷하게** 이동시킨다."""

_OPPOSITE_INTENT = """\
[반대 방향형 이상향 — 극단 반전]
현재 성향·관심을 **정반대 극단으로 크게 뒤집어** '필터버블 탈출'을 만든다.
- 성향 6축: 현재 높은 축은 크게 낮추고, 낮은 축은 크게 올린다(대략 100-현재 근처까지).
- 관심 도메인: 현재 많이 보는 상위 도메인은 크게 낮추고, 거의 안 보는 하위 도메인을 크게 올린다.
'적당히'가 아니라 **확연히 다른 사람**이 되게 한다. 균형형과 절대 겹치지 않게 극단으로 간다."""

_DEEPEN_INTENT = """\
[강점심화형 이상향 — 강점 증폭]
현재 강한 성향 축·상위 관심 도메인을 **더 끌어올려** 전문화·심화한다.
약한 축·하위 도메인은 거의 그대로 두고, 강점을 정체성으로 굳힌다."""

_BALANCE_INTENT = """\
[균형형(약점보완) 이상향]
현재 강점(강한 축·상위 도메인)은 유지하면서, 약하거나 저개발된 축·도메인만
자연스럽게 끌어올려 고르게 만든다. 강점을 깎지 않는다."""

_INTENT_BY_TYPE = {
    IdealType.OPPOSITE: _OPPOSITE_INTENT,
    IdealType.DEEPEN: _DEEPEN_INTENT,
    IdealType.BALANCE: _BALANCE_INTENT,
}


def build_propose_prompt(
    ideal_type: IdealType,
    *,
    profile_21: dict[str, float],
    disposition: dict[str, float],
    interest: dict[str, float],
    keywords: list[str] | None = None,
    persona_label: str = "",
    top_interests: dict[str, list] | None = None,
) -> str:
    intent = _INTENT_BY_TYPE.get(ideal_type, _BALANCE_INTENT)

    if disposition or interest:
        signal = ""
        if persona_label:
            signal += f"현재 별칭: {persona_label}\n"
        if keywords:
            signal += f"키워드: {', '.join(str(k) for k in keywords[:7])}\n"
        signal += (
            f"[현재 성향 6축]\n{render_disposition(disposition)}\n\n"
            f"[현재 관심 도메인]\n{render_domains(interest)}"
        )
    else:
        # portrait 없는 옛 스냅샷 폴백
        signal = f"[관심사]\n{render_interests(top_interests)}"

    return f"""당신은 Synapse 플랫폼의 Navigator 에이전트입니다.
사용자의 실제 소비 초상(성향 6축·관심 도메인)을 근거로 '이상향'을 설계합니다.

{intent}

[사용자 현재 초상]
{signal}

[참고: 현재 가치관·기질 13축(보조)]
{render_13axis(profile_21)}

{_OUTPUT_GUIDE}

reasoning은 축 나열식·기계적 서술을 피하고, 변화가 만드는 **경험·습관**이 그림처럼
그려지게 씁니다(예: "낯선 분야의 다큐를 일부러 찾아보며…"). 세 제안(반대/심화/균형)이
서로 확연히 다른 톤과 내용이 되게 하고, 같은 문장으로 시작하지 않습니다."""
