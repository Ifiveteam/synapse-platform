"""Archiver trace 공유 로거·포맷 유틸."""

from __future__ import annotations

import logging

from app.agents.archiver.constants import TRACE_PREVIEW_CHARS

logger = logging.getLogger("app.agents.archiver.workflow")

PREVIEW_CHARS = TRACE_PREVIEW_CHARS


def truncate(text: str | None, *, limit: int = PREVIEW_CHARS) -> str:
    if not text:
        return "(없음)"
    normalized = text.strip().replace("\r\n", "\n")
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}… [총 {len(normalized):,}자]"


def banner(title: str) -> None:
    line = "═" * 72
    logger.info("%s", line)
    logger.info("  %s", title)
    logger.info("%s", line)
