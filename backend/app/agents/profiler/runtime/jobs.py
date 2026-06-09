from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock

from app.agents.profiler.base import JobStatus, NotificationPayload, ProfilerResult
from app.agents.profiler.graph import run_profiler
from app.agents.profiler.runtime.insights import save_snapshot


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


class ProfilerJobStore:
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
            return self._profiles.get(user_id)

    def run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = JobStatus.RUNNING
            job.updated_at = datetime.now(UTC)

        try:
            final = run_profiler(job.user_id, job.notify_email)
            result = ProfilerResult(
                user_id=job.user_id,
                computed_at=datetime.now(UTC),
                axes=final["axes"],
                layer_b=final["layer_b"],
                top5_interests=final["top5_interests"],
                summary=final["summary"],
                interpretation=final["interpretation"],
                axis_notes=final.get("axis_notes", {}),
                investigation_log=final.get("investigation_log", []),
                llm_used=final.get("llm_used", False),
                behavior_patterns=final.get("behavior_patterns"),
            )
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
        except Exception as exc:  # noqa: BLE001 — job store must capture any pipeline failure
            with self._lock:
                job = self._jobs[job_id]
                job.status = JobStatus.FAILED
                job.error = str(exc)
                job.updated_at = datetime.now(UTC)


job_store = ProfilerJobStore()
