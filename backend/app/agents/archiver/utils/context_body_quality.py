"""활성 탭 본문 품질 휴리스틱 — CSS·코드 덩어리를 범용으로 걸러낸다."""

from __future__ import annotations

import re

from app.agents.archiver.core.constants import MIN_CLIENT_CONTEXT_BODY_CHARS, MIN_CONTEXT_BODY_QUALITY

_CODE_LINE_RE = re.compile(
    r"^\s*(var|let|const|function|import|export|@media|@keyframes)\b"
)


def _looks_like_css_selector(line: str) -> bool:
    """`.class`, `#id`, `@rule` 등 CSS 셀렉터 형태만 잡는다."""
    stripped = line.strip()
    if stripped.startswith((".", "#", "@")):
        return True
    if re.search(r"[\s>+~][.#][\w-]", stripped):
        return True
    return bool(re.match(r"^[\w-]+\s*\{", stripped))


def is_noise_line(line: str) -> bool:
    """한 줄이 CSS/코드 노이즈인지 범용 휴리스틱으로 판별한다."""
    stripped = line.strip()
    if len(stripped) < 2:
        return False

    if "{" in stripped and "}" in stripped:
        return True
    if stripped.count(";") >= 2 and ":" in stripped:
        return True
    if _looks_like_css_selector(stripped):
        return True
    if _CODE_LINE_RE.match(stripped):
        return True

    non_ws = len(stripped.replace(" ", ""))
    if non_ws == 0:
        return True

    code_chars = sum(stripped.count(char) for char in "{};:")
    return code_chars / non_ws > 0.15


def filter_noise_lines(text: str) -> str:
    """노이즈 라인을 제거한 읽기 가능한 본문을 반환한다."""
    kept = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not is_noise_line(line)
    ]
    return "\n".join(kept)


def score_line_density(text: str) -> float:
    """SPA 껍데기(짧은 네비·빈 컨테이너) 패널티 — 0.0~1.0."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return 0.0

    substantive = [line for line in lines if len(line) >= 12]
    avg_len = sum(len(line) for line in lines) / len(lines)
    unique_ratio = len({line.lower() for line in lines}) / len(lines)
    substantive_ratio = len(substantive) / len(lines)

    if len(lines) >= 8 and avg_len < 18 and substantive_ratio < 0.35:
        return 0.15
    if len(lines) >= 15 and unique_ratio < 0.25 and substantive_ratio < 0.5:
        return 0.2

    return min(
        1.0,
        substantive_ratio * 0.5
        + unique_ratio * 0.25
        + min(avg_len / 80.0, 1.0) * 0.25,
    )


def score_context_body_quality(text: str) -> float:
    """0.0~1.0 — 자연어 비율·노이즈 잔존량·중괄호 밀도를 종합한다."""
    normalized = text.strip()
    if not normalized:
        return 0.0

    filtered = filter_noise_lines(normalized)
    if len(filtered) < MIN_CLIENT_CONTEXT_BODY_CHARS:
        return 0.0

    retention = len(filtered) / len(normalized)
    natural_chars = sum(
        1
        for char in filtered
        if char.isalpha() or "\uac00" <= char <= "\ud7a3" or char.isspace()
    )
    natural_ratio = natural_chars / len(filtered)
    brace_density = (filtered.count("{") + filtered.count("}")) / len(filtered)
    line_density = score_line_density(filtered)

    score = (
        retention * 0.25
        + natural_ratio * 0.45
        + max(0.0, 1.0 - brace_density * 20.0) * 0.15
        + line_density * 0.15
    )
    return min(1.0, max(0.0, score))


def is_meaningful_context_body(text: str | None) -> bool:
    """길이·품질 기준을 모두 통과하는지 판별한다."""
    normalized = (text or "").strip()
    if len(normalized) < MIN_CLIENT_CONTEXT_BODY_CHARS:
        return False
    if score_line_density(normalized) < 0.2:
        return False
    return score_context_body_quality(normalized) >= MIN_CONTEXT_BODY_QUALITY


def prepare_context_body(text: str | None) -> str | None:
    """노이즈 제거 후 품질 검사를 통과한 본문을 반환한다."""
    normalized = (text or "").strip()
    if not normalized:
        return None

    filtered = filter_noise_lines(normalized)
    candidate = (
        filtered
        if len(filtered) >= MIN_CLIENT_CONTEXT_BODY_CHARS
        else normalized
    )
    if not is_meaningful_context_body(candidate):
        return None
    return candidate
