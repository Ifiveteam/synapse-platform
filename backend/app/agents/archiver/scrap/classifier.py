"""Archiver 스크랩 Gemini 요약·분류 파이프라인."""

from __future__ import annotations

from app.agents.archiver.scrap.models import ScrapClassificationResult
from app.agents.archiver.scrap.prompts import SCRAP_CLASSIFY_SYSTEM_PROMPT
from app.agents.shared.gemini import GEMINI_MODEL, invoke_structured_safe

RAW_BODY_MAX_CHARS = 5000
SUMMARY_MAX_CHARS = 120
CATEGORY_MAX_CHARS = 512
SCRAP_CLASSIFY_TEMPERATURE = 0.2
SCRAP_CLASSIFY_MAX_OUTPUT_TOKENS = 2048

_FALLBACK_CATEGORY = "기타"
_FALLBACK_SUMMARY = "요약을 생성하지 못했습니다."


def clamp_field(value: str, *, max_chars: int) -> str:
    """DB·프롬프트 한도에 맞게 문자열을 자른다."""
    normalized = value.strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars]


def truncate_raw_body(body: str | None, *, max_chars: int = RAW_BODY_MAX_CHARS) -> str:
    """Gemini·DB 저장용 원문을 안전하게 자른다."""
    normalized = (body or "").strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars]


def normalize_tags(tags: list[str]) -> list[str]:
    """중복 제거·공백 정리 후 태그 목록을 반환한다."""
    seen: set[str] = set()
    normalized: list[str] = []
    for tag in tags:
        cleaned = tag.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized[:7]


def _fallback_classification() -> ScrapClassificationResult:
    return ScrapClassificationResult(
        summary=_FALLBACK_SUMMARY,
        category=_FALLBACK_CATEGORY,
        tags=[],
    )


def normalize_custom_category(value: str | None) -> str | None:
    """유저·Tool이 지정한 카테고리 문자열을 DB 한도에 맞게 정규화한다."""
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return clamp_field(normalized, max_chars=CATEGORY_MAX_CHARS)


async def classify_scrap_content(
    user_content: str,
    *,
    custom_category: str | None = None,
) -> ScrapClassificationResult:
    """본문을 Gemini Structured Output으로 요약·분류한다.

    custom_category가 있으면 카테고리 추론을 생략하고 해당 값을 그대로 사용한다.
    """
    trimmed = truncate_raw_body(user_content)
    if not trimmed:
        return _fallback_classification()

    override_category = normalize_custom_category(custom_category)

    result = await invoke_structured_safe(
        system_instruction=SCRAP_CLASSIFY_SYSTEM_PROMPT,
        user_content=trimmed,
        schema=ScrapClassificationResult,
        temperature=SCRAP_CLASSIFY_TEMPERATURE,
        model=GEMINI_MODEL,
        max_output_tokens=SCRAP_CLASSIFY_MAX_OUTPUT_TOKENS,
        fallback_factory=_fallback_classification,
    )
    if result is None:
        return _fallback_classification()

    resolved_category = (
        override_category
        if override_category
        else clamp_field(
            result.category.strip() or _FALLBACK_CATEGORY,
            max_chars=CATEGORY_MAX_CHARS,
        )
    )

    return ScrapClassificationResult(
        summary=clamp_field(
            result.summary.strip() or _FALLBACK_SUMMARY,
            max_chars=SUMMARY_MAX_CHARS,
        ),
        category=resolved_category,
        tags=normalize_tags(list(result.tags)),
    )
