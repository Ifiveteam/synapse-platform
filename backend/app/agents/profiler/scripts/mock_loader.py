"""Mock persona JSON loader (MVP). Replace with Indexer API integration."""

from __future__ import annotations

import json
from pathlib import Path

from app.agents.profiler.base import IndexedRecordsBundle, PersonaInfo

MOCKS_DIR = Path(__file__).resolve().parent.parent / "mocks"


def load_mock_bundle(user_id: str) -> IndexedRecordsBundle:
    path = MOCKS_DIR / f"{user_id}.json"
    if not path.exists():
        msg = f"Mock persona not found: {user_id}"
        raise FileNotFoundError(msg)
    data = json.loads(path.read_text(encoding="utf-8"))
    return IndexedRecordsBundle.model_validate(data)


def list_personas() -> list[PersonaInfo]:
    manifest_path = MOCKS_DIR / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [PersonaInfo.model_validate(item) for item in data["personas"]]
