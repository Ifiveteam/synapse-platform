"""라우터 preflight·직전 대화 포함 여부 휴리스틱."""

from __future__ import annotations

import re

from app.agents.archiver.models import (
    ArchiverState,
    has_prior_dialogue,
    recent_dialogue_snippet,
)

_GREETING_PATTERN = re.compile(
    r"^(?:"
    r"ㅎㅇ|하이|안녕(?:하세요|하십니까)?|헬로|"
    r"hi|hello|hey|"
    r"고마워|고맙습니다|감사(?:합니다|해)?|thanks?(?:\s+you)?|"
    r"ㅋ+|ㅎ+|ㅇㅋ|ok(?:ay)?"
    r")[!?.~ㅋㅎ\s]*$",
    re.IGNORECASE,
)

_DEICTIC_OR_FOLLOWUP_PATTERN = re.compile(
    r"(?:"
    r"이거|그거|저거|여기|거기|저기|"
    r"방금|위에|아까|"
    r"이게|그게|이건|그건|이것|그것|"
    r"더\s*쉽게|다시\s*설명|다시\s*말|한번\s*더|"
    r"(?:왜|진짜|그래|맞아)\?"
    r")",
    re.IGNORECASE,
)

_GREETING_MAX_LEN = 24


def is_greeting_preflight(message: str) -> bool:
    """인사·감사·짧은 리액션 — LLM 없이 GENERAL로 처리한다."""
    stripped = message.strip()
    if not stripped or len(stripped) > _GREETING_MAX_LEN:
        return False
    return bool(_GREETING_PATTERN.match(stripped))


def needs_dialogue_context(message: str) -> bool:
    """지시어·후속 질문 등 직전 대화 맥락이 라우팅에 필요한지 판별한다."""
    stripped = message.strip()
    if not stripped:
        return False
    return bool(_DEICTIC_OR_FOLLOWUP_PATTERN.search(stripped))


def resolve_router_dialogue_context(
    state: ArchiverState,
    message: str,
) -> str | None:
    """라우터 프롬프트에 넣을 직전 대화 — 멀티턴 또는 지시어 후속이면 포함."""
    snippet = recent_dialogue_snippet(state)
    if snippet == "(없음)":
        return None
    if has_prior_dialogue(state) or needs_dialogue_context(message):
        return snippet
    return None
