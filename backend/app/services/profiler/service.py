"""Profiler job orchestration and DB-backed profile reads."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from app.agents.profiler.facade import get_profiler_agent
from app.models.user_profile_history import UserProfileHistory
from app.schemas.profiler import JobStatus
from app.services.notification import NotificationPayload
from app.services.profiler.scores import history_scores_dict

# 동시 프로파일 분석 실행 상한 (외부 API·DB 폭주 방지)
_MAX_CONCURRENT_JOBS = 2


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
        "top_categories": [],
        "top_channels": [],
    }


async def profile_dict_with_catalog(session, row: UserProfileHistory) -> dict[str, Any]:
    from app.repositories.indexer_repository import (
        fetch_top_categories,
        fetch_top_channels,
    )

    data = profile_to_dict(row)
    data["top_categories"] = await fetch_top_categories(session, row.user_id)
    data["top_channels"] = await fetch_top_channels(session, row.user_id)
    return data


@dataclass
class ProfilerJob:
    job_id: str
    user_id: str
    notify_email: str
    analysis_source_id: str | None = None
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
        self.agent = get_profiler_agent()
        # fire-and-forget 태스크의 강한 참조 유지 (GC 수거로 인한 메일 누락 방지)
        self._bg_tasks: set[asyncio.Task[None]] = set()
        # 동시 실행 제한 — 대기 job은 PENDING 유지
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT_JOBS)

    def create_job(
        self,
        user_id: str,
        email: str = "",
        *,
        analysis_source_id: str | None = None,
    ) -> ProfilerJob:
        job = ProfilerJob(
            job_id=str(uuid.uuid4()),
            user_id=user_id,
            notify_email=email,
            analysis_source_id=analysis_source_id,
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
            return await profile_dict_with_catalog(session, row)

    async def list_analyses_async(self, user_id: str) -> list[dict[str, Any]]:
        from app.core.database.session import AsyncSessionLocal
        from app.models.user_analysis_source import AnalysisSourceStage
        from app.repositories.analysis_source_repository import fetch_running_sources
        from app.repositories.profiler_repository import fetch_profile_history_list

        uid = uuid.UUID(user_id)
        async with AsyncSessionLocal() as session:
            running = await fetch_running_sources(session, uid)
            rows = await fetch_profile_history_list(session, uid)

        total = len(rows)
        items: list[dict[str, Any]] = []
        # 진행 중 소스 — 분류중/분석중 (DB 기반이라 재시작에도 유지)
        for src in running:
            indexing = src.stage == AnalysisSourceStage.INDEXING
            if indexing:
                title = (
                    f"{src.file_name} 분류 중" if src.file_name else "파일 분류 중"
                )
            else:
                title = "프로파일 분석 중"
            items.append(
                {
                    "id": str(src.id),
                    "title": title,
                    "snapshot_date": None,
                    "status": "running",
                    "stage": src.stage,
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
            return await profile_dict_with_catalog(session, row)

    async def run_job_async(self, job_id: str) -> None:
        # 세마포어로 동시 실행 제한 — 슬롯 대기 동안 job은 PENDING 유지
        async with self._semaphore:
            with self._lock:
                job = self._jobs.get(job_id)
                if job is None:
                    return
                job.status = JobStatus.RUNNING
                job.updated_at = datetime.now(UTC)
                user_id = job.user_id
                notify_email = job.notify_email
                analysis_source_id = job.analysis_source_id

            try:
                final = await self.agent.run_profile(user_id, notify_email)
                profile = await self.fetch_profile_async(user_id)
                notification = final.get("notification")
                if profile and analysis_source_id:
                    from app.services.analysis_source_service import (
                        complete_source_async,
                    )

                    await complete_source_async(
                        analysis_source_id, profile.get("snapshot_id")
                    )
                with self._lock:
                    job = self._jobs[job_id]
                    job.status = JobStatus.COMPLETED
                    job.current_step = final.get("current_step", "notify")
                    job.result = profile
                    job.notification = notification
                    job.updated_at = datetime.now(UTC)
            except Exception as exc:  # noqa: BLE001
                if analysis_source_id:
                    from app.services.analysis_source_service import (
                        fail_source_async,
                    )

                    await fail_source_async(analysis_source_id)
                with self._lock:
                    job = self._jobs[job_id]
                    job.status = JobStatus.FAILED
                    job.error = str(exc)
                    job.updated_at = datetime.now(UTC)

    def enqueue_for_user(
        self,
        user_id: str,
        email: str = "",
        *,
        analysis_source_id: str | None = None,
    ) -> ProfilerJob:
        job = self.create_job(user_id, email, analysis_source_id=analysis_source_id)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.run_job_async(job.job_id))
        else:
            # 강한 참조 유지 — GC가 실행 중 태스크를 수거하지 않도록 (메일 누락 방지)
            task = loop.create_task(self.run_job_async(job.job_id))
            self._bg_tasks.add(task)
            task.add_done_callback(self._bg_tasks.discard)
        return job


profiler_service = ProfilerService()
