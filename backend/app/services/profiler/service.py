"""Profiler job orchestration and DB-backed profile reads."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from app.agents.profiler.graph import run_profiler_async
from app.models.user_profile_history import UserProfileHistory
from app.schemas.profiler import JobStatus
from app.services.notification import NotificationPayload

SCORE_FIELDS = (
    "self_direction",
    "stimulation",
    "achievement",
    "power",
    "security",
    "benevolence",
    "universalism",
    "hedonism",
    "conformity",
    "tradition",
    "novelty_seeking",
    "persistence",
    "self_transcendence",
    "exploration",
    "analytical",
    "creativity",
    "execution",
    "achievement_drive",
    "autonomy",
    "sociality",
    "sensitivity",
)


def history_scores_dict(history) -> dict[str, float]:
    return {
        key: float(getattr(history, key) or 0.0)
        for key in SCORE_FIELDS
        if getattr(history, key) is not None
    }


def profile_to_dict(row: UserProfileHistory) -> dict[str, Any]:
    traits = row.dominant_traits
    if isinstance(traits, dict):
        traits = list(traits.values()) if traits else []
    return {
        "user_id": str(row.user_id),
        "snapshot_id": str(row.id),
        "snapshot_date": row.snapshot_date,
        "scores": history_scores_dict(row),
        "summary_text": row.summary_text or "",
        "persona_label": row.persona_label,
        "behavior_reasoning": row.behavior_reasoning,
        "dominant_traits": traits,
        "supporting_evidence": row.supporting_evidence,
        "tone_of_user": row.tone_of_user,
    }


@dataclass
class ProfilerJob:
    job_id: str
    user_id: str
    notify_email: str
    status: JobStatus = JobStatus.PENDING
    current_step: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    result: dict[str, Any] | None = None
    error: str | None = None
    notification: NotificationPayload | None = None


class ProfilerService:
    def __init__(self) -> None:
        self._jobs: dict[str, ProfilerJob] = {}
        self._lock = Lock()

    def create_job(self, user_id: str, email: str = "") -> ProfilerJob:
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

    async def fetch_profile_async(self, user_id: str) -> dict[str, Any] | None:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.profiler_repository import fetch_latest_profile

        uid = uuid.UUID(user_id)
        async with AsyncSessionLocal() as session:
            row = await fetch_latest_profile(session, uid)
        if row is None:
            return None
        return profile_to_dict(row)

    def get_profile(self, user_id: str) -> dict[str, Any] | None:
        return asyncio.run(self.fetch_profile_async(user_id))

    def list_jobs_for_user(self, user_id: str) -> list[ProfilerJob]:
        with self._lock:
            return [
                job
                for job in self._jobs.values()
                if job.user_id == user_id
                and job.status in (JobStatus.PENDING, JobStatus.RUNNING)
            ]

    async def list_analyses_async(self, user_id: str) -> list[dict[str, Any]]:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.profiler_repository import fetch_profile_history_list

        uid = uuid.UUID(user_id)
        async with AsyncSessionLocal() as session:
            rows = await fetch_profile_history_list(session, uid)

        total = len(rows)
        items: list[dict[str, Any]] = []
        for job in sorted(
            self.list_jobs_for_user(user_id),
            key=lambda j: j.created_at,
            reverse=True,
        ):
            items.append(
                {
                    "id": job.job_id,
                    "title": "프로파일 분석 진행 중",
                    "snapshot_date": None,
                    "status": (
                        "pending" if job.status == JobStatus.PENDING else "running"
                    ),
                    "kind": "job",
                }
            )

        for index, row in enumerate(rows):
            number = total - index
            title = row.persona_label or f"개인성향 분석 #{number}"
            items.append(
                {
                    "id": str(row.id),
                    "title": title,
                    "snapshot_date": row.snapshot_date,
                    "status": "completed",
                    "kind": "snapshot",
                }
            )
        return items

    def list_analyses(self, user_id: str) -> list[dict[str, Any]]:
        return asyncio.run(self.list_analyses_async(user_id))

    async def fetch_snapshot_async(
        self, user_id: str, snapshot_id: str
    ) -> dict[str, Any] | None:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.profiler_repository import fetch_profile_snapshot

        uid = uuid.UUID(user_id)
        sid = uuid.UUID(snapshot_id)
        async with AsyncSessionLocal() as session:
            row = await fetch_profile_snapshot(session, uid, sid)
        if row is None:
            return None
        return profile_to_dict(row)

    def get_snapshot(self, user_id: str, snapshot_id: str) -> dict[str, Any] | None:
        return asyncio.run(self.fetch_snapshot_async(user_id, snapshot_id))

    def run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = JobStatus.RUNNING
            job.updated_at = datetime.now(UTC)

        try:
            final = asyncio.run(run_profiler_async(job.user_id, job.notify_email))
            profile = asyncio.run(self.fetch_profile_async(job.user_id))
            notification = final.get("notification")
            with self._lock:
                job = self._jobs[job_id]
                job.status = JobStatus.COMPLETED
                job.current_step = final.get("current_step", "notify")
                job.result = profile
                job.notification = notification
                job.updated_at = datetime.now(UTC)
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                job = self._jobs[job_id]
                job.status = JobStatus.FAILED
                job.error = str(exc)
                job.updated_at = datetime.now(UTC)

    def enqueue_for_user(self, user_id: str, email: str = "") -> ProfilerJob:
        job = self.create_job(user_id, email)
        import threading

        threading.Thread(target=self.run_job, args=(job.job_id,), daemon=True).start()
        return job


profiler_service = ProfilerService()
