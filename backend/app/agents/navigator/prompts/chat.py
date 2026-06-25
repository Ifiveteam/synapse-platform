"""대화형 이상향 설계 프롬프트 (interpret / respond)."""

from __future__ import annotations

from typing import Any

from app.agents.navigator.prompts import (
    render_8axis,
    render_13axis,
    render_profile_21,
)

_WORKING_NOTE = (
    "(아직 조율 중인 이상향이 없습니다 — 사용자의 요청을 반영해 처음 제안하세요.)"
)


def _render_working(state: dict[str, Any]) -> str:
    working = state.get("working_ideal")
    if not working:
        return _WORKING_NOTE
    return render_8axis(working)


def _render_working_values(state: dict[str, Any]) -> str:
    working = state.get("working_values")
    if not working:
        return _WORKING_NOTE
    return render_13axis(working)


def build_interpret_prompt(state: dict[str, Any]) -> str:
    """유저 메시지 → 이상향 13축(가치관·기질) 조정(Structured Output) 추출 프롬프트."""
    return f"""당신은 Navigator 에이전트입니다. 사용자와 대화하며 이상향을 **가치관 10축 + 기질 3축(0~100)** 으로 조율합니다.
행동 8축(탐색·분석·창의 등)은 이 13축에서 시스템이 자동 파생하므로 직접 출력하지 않습니다.
사용자의 말이 차트에 **즉시 반영**되어야 하므로, 방향성이 조금이라도 드러나면 적극적으로 값을 조정하세요.

[현재 가치관·기질 13축]
{render_13axis(state.get("profile_21", {}))}

[현재 조율 중인 이상향 13축]
{_render_working_values(state)}

사용자의 최신 메시지를 해석해, 조정 후의 **이상향 13축 전체(updated_design)** 를 출력하세요.

판단 기준:
- 사용자가 방향성(올리기/낮추기/더/덜/강화/완화/균형, 또는 "차분하게·도전적으로" 같은 무드)을 조금이라도 드러내면 → **changed=true** 로 두고 관련 축을 실제로 조정합니다.
  - 행동 표현(예: "창의를 더", "사회성 낮춰")이면 그 행동과 연결된 가치관·기질 축(예: 창의↔자기지향·자극·쾌락 / 사회성↔친선·보편)을 움직여 반영합니다.
- 구체 수치를 주면 반영하고, 수치 없이 "더/조금/훨씬"이면 **체감되는 폭(보통 10~20점, "훨씬"이면 그 이상)** 으로 움직입니다.
- 직접 언급되지 않은 축은 그대로 유지합니다(임의로 건드리지 말 것).
- 오직 순수한 정보·설명 질문일 때만 changed=false 로 두고 현재 값을 유지합니다.
- 모든 축은 0~100 범위를 지킵니다. reasoning에는 무엇을 어떻게 바꿨는지 한국어로 간단히 적습니다.
- persona_label에는 조정된 이상향을 한마디로 부르는 짧은 한국어 명칭(5~12자, 예: "창의적인 탐색가")을 적습니다."""


def build_chat_system_prompt(state: dict[str, Any]) -> str:
    """respond 노드 — 자연어 답변 생성용 시스템 프롬프트."""
    return f"""당신은 Synapse 플랫폼의 Navigator 에이전트입니다.
사용자가 자신의 '이상적인 콘텐츠 소비 성향(이상향)'을 설계하도록 친근하게 돕습니다.

[사용자 현재 21축 프로필]
{render_profile_21(state.get("profile_21", {}))}

[현재 조율 중인 이상향(행동 8축)]
{_render_working(state)}

규칙:
- 위 [현재 조율 중인 이상향]은 사용자의 방금 요청을 **이미 반영한 결과**이며 화면의 스파이더 차트도 이미 갱신되었습니다. 따라서 "올려볼까요?"처럼 아직 안 한 것처럼 되묻지 말고, **방금 반영한 변화를 완료형으로 확인**해 줍니다(예: "창의 축을 더 끌어올렸어요").
- 변화가 어떤 의미인지(콘텐츠 소비가 어떻게 달라지는지) 한국어로 자연스럽게 전달하고, 점수 숫자 나열은 피합니다.
- 마지막에 다음으로 더 조율하면 좋을 축 한 가지를 가볍게 제안합니다(강요하지 않음).
- 과장 없이 따뜻하고 간결한 톤으로 답합니다."""
