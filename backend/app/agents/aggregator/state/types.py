"""Aggregator LangGraph 공유 타입·상수."""

from __future__ import annotations

from typing import Literal

RevisionTarget = Literal[
    "generate_report",
    "culture_analysis",
    "market_analysis",
    "both_analyses",
]

MAX_REVIEW_ATTEMPTS = 3
REVIEW_PASS_THRESHOLD = 80
