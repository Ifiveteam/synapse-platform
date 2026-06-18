from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class CompareState(TypedDict):
    user_id: str
    from_snapshot_id: str
    to_snapshot_id: str

    from_row: NotRequired[Any]
    to_row: NotRequired[Any]
    diff: NotRequired[dict[str, Any]]
    narrative: NotRequired[dict[str, Any]]
    narrative_error: NotRequired[str | None]
    error: NotRequired[str | None]
    run_log: NotRequired[list[str]]
