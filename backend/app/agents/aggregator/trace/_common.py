"""Aggregator trace 공유 로거·포맷 유틸."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("app.agents.aggregator.workflow")

PREVIEW_CHARS = 600
KEYWORD_PREVIEW = 5


def truncate(text: str | None, *, limit: int = PREVIEW_CHARS) -> str:
    if not text:
        return "(없음)"
    normalized = text.strip().replace("\r\n", "\n")
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}… [총 {len(normalized):,}자]"


def keyword_lines(
    items: list[dict[str, Any]], *, label_key: str = "keyword"
) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(items[:KEYWORD_PREVIEW], start=1):
        keyword = item.get(label_key, "?")
        extra_parts: list[str] = []
        for key in ("rank", "frequency", "interest_index", "category", "source"):
            if key in item and item[key] is not None:
                extra_parts.append(f"{key}={item[key]}")
        suffix = f" ({', '.join(extra_parts)})" if extra_parts else ""
        lines.append(f"    {index}. {keyword}{suffix}")
    if len(items) > KEYWORD_PREVIEW:
        lines.append(f"    … 외 {len(items) - KEYWORD_PREVIEW}건")
    return lines


def banner(title: str) -> None:
    line = "═" * 72
    logger.info("%s", line)
    logger.info("  %s", title)
    logger.info("%s", line)
