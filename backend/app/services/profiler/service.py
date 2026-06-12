"""Profiler job orchestration, agent invocation, and profile persistence."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from app.agents.profiler.base import (
    JobStatus,
    NotificationPayload,
    ProfilerResult,
    ProfilerSnapshot,
    profiler_result_from_state,
)
from app.agents.profiler.graph import run_profiler

_MOCKS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "agents" / "profiler" / "mocks"
)
_SNAPSHOTS_DIR = _MOCKS_DIR / "snapshots"


def _user_snapshot_dir(user_id: str) -> Path:
    return _SNAPSHOTS_DIR / user_id


def list_snapshot_versions(user_id: str) -> list[str]:
    directory = _user_snapshot_dir(user_id)
    if not directory.exists():
        return []
    return sorted(path.stem for path in directory.glob("*.json"))


def load_snapshot(user_id: str, version: str) -> ProfilerSnapshot | None:
    path = _user_snapshot_dir(user_id) / f"{version}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProfilerSnapshot.model_validate(data)


def save_snapshot(
    user_id: str, result: ProfilerResult, version: str | None = None
) -> str:
    directory = _user_snapshot_dir(user_id)
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


@dataclass
class ProfilerJob:
    job_id: str
    user_id: str
    notify_email: str
    status: JobStatus = JobStatus.PENDING
    current_step: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    result: ProfilerResult | None = None
    error: str | None = None
    notification: NotificationPayload | None = None


class ProfilerService:
    def __init__(self) -> None:
        self._jobs: dict[str, ProfilerJob] = {}
        self._profiles: dict[str, ProfilerResult] = {}
        self._lock = Lock()

    def create_job(self, user_id: str, email: str) -> ProfilerJob:
        job = ProfilerJob(
            job_id=str(uuid.uuid4()),
            user_id=user_id,
            notify_email=email,
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> ProfilerJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def get_profile(self, user_id: str) -> ProfilerResult | None:
        with self._lock:
            cached = self._profiles.get(user_id)
        if cached is not None:
            return cached
        versions = list_snapshot_versions(user_id)
        if not versions:
            return None
        snapshot = load_snapshot(user_id, versions[-1])
        if snapshot is None:
            return None
        return snapshot.result

    def run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = JobStatus.RUNNING
            job.updated_at = datetime.now(UTC)

        try:
            final = run_profiler(job.user_id, job.notify_email)
            result = profiler_result_from_state(final)
            save_snapshot(job.user_id, result)
            notification = final.get("notification")
            with self._lock:
                job = self._jobs[job_id]
                job.status = JobStatus.COMPLETED
                job.current_step = final.get("current_step", "notify")
                job.result = result
                job.notification = notification
                job.updated_at = datetime.now(UTC)
                self._profiles[job.user_id] = result
        except Exception as exc:  # noqa: BLE001 — must capture any pipeline failure
            with self._lock:
                job = self._jobs[job_id]
                job.status = JobStatus.FAILED
                job.error = str(exc)
                job.updated_at = datetime.now(UTC)


profiler_service = ProfilerService()
