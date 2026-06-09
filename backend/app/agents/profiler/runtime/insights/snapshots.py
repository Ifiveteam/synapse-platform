from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.agents.profiler.base import ProfilerResult, ProfilerSnapshot

SNAPSHOTS_DIR = Path(__file__).resolve().parent.parent.parent / "mocks" / "snapshots"


def _user_dir(user_id: str) -> Path:
    return SNAPSHOTS_DIR / user_id


def list_snapshot_versions(user_id: str) -> list[str]:
    directory = _user_dir(user_id)
    if not directory.exists():
        return []
    versions = sorted(path.stem for path in directory.glob("*.json"))
    return versions


def load_snapshot(user_id: str, version: str) -> ProfilerSnapshot | None:
    path = _user_dir(user_id) / f"{version}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProfilerSnapshot.model_validate(data)


def save_snapshot(
    user_id: str, result: ProfilerResult, version: str | None = None
) -> str:
    directory = _user_dir(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    if version is None:
        version = datetime.now(UTC).strftime("v%Y%m%d-%H%M%S")
    snapshot = ProfilerSnapshot(
        version=version,
        user_id=user_id,
        computed_at=result.computed_at,
        result=result,
    )
    path = directory / f"{version}.json"
    path.write_text(
        json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return version
