"""이상향 자동 제안 프롬프트 (반대 / 강점심화 / 균형)."""

from __future__ import annotations

from app.agents.navigator.prompts import (
    render_8axis,
    render_interests,
    render_profile_21,
)
from app.agents.navigator.schemas import IdealType

_AXIS_GUIDE = """\
출력은 이상향의 **가치관 10축 + 기질 3축**(각 0~100)으로 설계한다:
[가치관] self_direction(자기지향), stimulation(자극), achievement(성취), power(권력),
security(안전), benevolence(친선), universalism(보편), hedonism(쾌락),
conformity(순응), tradition(전통)
[기질] novelty_seeking(탐구성), persistence(지속성), self_transcendence(자기초월)
행동 8축(탐색·분석·창의·실행·성취·자율·사회성·감수성)은 시스템이 이 13축에서
자동으로 파생하므로 **출력하지 않는다**. 현재 13축을 기준으로 위 의도에 맞게 조정한다."""

_OPPOSITE_INTENT = """\
[반대 방향형 이상향]
현재 두드러진 축은 의도적으로 낮추고, 약한 축은 끌어올려 '필터버블 탈출'을 유도한다.
단, 사용자의 가치관·기질과 완전히 충돌하지 않는 현실적 범위에서 조정한다."""

_DEEPEN_INTENT = """\
[강점심화형 이상향]
현재 두드러진(강한) 축을 더 끌어올려 '전문화·심화'를 유도한다.
약한 축은 거의 그대로 두고, 강점을 정체성으로 굳히는 방향으로 설계한다."""

_BALANCE_INTENT = """\
[균형형(약점보완) 이상향]
현재 강점은 유지하면서, 약하거나 저개발된 축만 자연스럽게 끌어올려 '균형'을 잡는다.
강점을 깎지 않고 부족한 부분을 보완하는 방향으로 설계한다."""

_INTENT_BY_TYPE = {
    IdealType.OPPOSITE: _OPPOSITE_INTENT,
    IdealType.DEEPEN: _DEEPEN_INTENT,
    IdealType.BALANCE: _BALANCE_INTENT,
}


def build_propose_prompt(
    ideal_type: IdealType,
    profile_21: dict[str, float],
    top_interests: dict[str, list] | None,
) -> str:
    intent = _INTENT_BY_TYPE.get(ideal_type, _BALANCE_INTENT)
    return f"""당신은 Synapse 플랫폼의 Navigator 에이전트입니다.
사용자의 21축 성향 프로필을 근거로 '이상향(목표 행동 8축)'을 설계합니다.

{intent}

[현재 21축 프로필]
{render_profile_21(profile_21)}

[현재 행동 8축]
{render_8axis(profile_21)}

[관심사]
{render_interests(top_interests)}

{_AXIS_GUIDE}

persona_label에는 이 이상향을 한마디로 부르는 짧고 직관적인 한국어 페르소나 명칭을 적는다
(형식 예: "창의적인 탐색가", "균형 잡힌 큐레이터" — 5~12자, 과장 없이).

reasoning은 아래 **흐름**을 따르되, 문장은 템플릿처럼 딱딱하지 않게 자유롭고 자연스럽게 쓴다
(3~5문장, 한국어):
1) 먼저 이 **페르소나(이상향)가 어떤 성향의 사람인지** 설명한다 — 이 이상향 자체의
   정체성·태도, 콘텐츠를 어떻게 소비하는 사람인지를 생생하게.
2) 이어서 **현재 사용자님의 ○○한 성향**을 짚고, 이 이상향이 그 위에서 어떤 면을
   채워주는지 / 확장하는지 / 전환하는지를 자연스럽게 연결해 설명한다.

지킬 것:
- "자기지향·자극을 유지하되 보편성을 끌어올렸다" 같은 **축 나열식·기계적 서술 금지**.
  변화가 만드는 **경험·습관**이 그림처럼 그려지게 쓴다 (예: "낯선 분야의 다큐를 일부러 찾아보며…").
- 세 제안(반대/심화/균형)이 서로 **확연히 다른 톤과 내용**이 되게 하고, 같은 문장으로 시작하지 않는다.
- "사용자님"은 자연스럽게 쓰되 매 문장 반복하지 않는다."""
