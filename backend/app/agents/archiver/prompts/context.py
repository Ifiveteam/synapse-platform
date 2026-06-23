"""Archiver 프롬프트 공통 컨텍스트 — 현재 시각 등."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

_KST = timezone(timedelta(hours=9))


def format_archiver_current_date() -> str:
    """한국 시간 기준 오늘 날짜 (예: 2026년 6월 19일)."""
    now = datetime.now(_KST)
    return f"{now.year}년 {now.month}월 {now.day}일"
