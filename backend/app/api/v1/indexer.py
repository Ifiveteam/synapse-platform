import os
import tempfile
import uuid as uuid_mod
from collections import Counter
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.indexer.graph import graph
from app.api.v1.auth import get_current_user_dep
from app.core.database.session import get_db
from app.repositories.analysis_source_repository import begin_source
from app.services.analysis_source_service import (
    fail_source_async,
    upload_source_key,
)
from app.services.indexer_service import indexer_service

router = APIRouter(prefix="/indexer", tags=["indexer"])

analysis_status: dict = {}


def _temp_upload_path(file: UploadFile) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".zip", ".json"}:
        suffix = ".json"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        return tmp.name


async def run_analysis(
    task_id: str,
    tmp_path: str,
    user_id: UUID,
    user_email: str,
    analysis_source_id: str,
):
    """백그라운드 인덱싱 실행 (프로파일러는 IndexerService가 profile-once로 트리거)."""
    try:
        analysis_status[task_id] = {"status": "running"}

        result = await graph.ainvoke(
            {
                "json_path": tmp_path,
                "raw_data": [],
                "cleaned_data": [],
                "error": None,
                "saved_count": None,
                "user_id": user_id,
                "analysis_source_id": analysis_source_id,
            }
        )

        os.unlink(tmp_path)

        if result["error"]:
            analysis_status[task_id] = {"status": "error", "message": result["error"]}
            await fail_source_async(analysis_source_id)
            return

        cleaned = result.get("cleaned_data") or []
        category_stats = dict(
            Counter(
                str(item.get("youtube_category_id") or "unknown") for item in cleaned
            ).most_common()
        )
        shorts_count = sum(1 for item in cleaned if item.get("is_shorts"))

        analysis_status[task_id] = {
            "status": "success",
            "total": len(result.get("raw_data") or []),
            "processed": result.get("saved_count"),
            "raw_count": len(result.get("raw_data") or []),
            "filtered_count": result.get("filtered_count") or len(cleaned),
            "cleaned_count": len(cleaned),
            "shorts_count": shorts_count,
            "category_stats": category_stats,
        }

        # 프로파일러 트리거는 IndexerService가 profile-once 정책으로 처리.
    except Exception as e:
        analysis_status[task_id] = {"status": "error", "message": str(e)}
        await fail_source_async(analysis_source_id)


async def _start_upload_analysis(
    *,
    session: AsyncSession,
    background_tasks: BackgroundTasks,
    user,
    content: bytes,
    filename: str | None,
    tmp_path: str,
    mode: str | None = None,
    batch_id: str | None = None,
) -> dict:
    source_key = upload_source_key(content)
    row, action = await begin_source(
        session, user.id, source_key, filename, batch_id=batch_id
    )
    await session.commit()

    if action == "skip_completed":
        os.unlink(tmp_path)
        return {
            "status": "already_completed",
            "profile_history_id": (
                str(row.profile_history_id) if row.profile_history_id else None
            ),
        }
    if action in ("skip_running", "skip_pending"):
        os.unlink(tmp_path)
        return {"status": "already_running"}

    # 유저별 직렬 큐에 등록 — 같은 유저는 하나씩 순차 인덱싱 (동시 교착 방지)
    task_id = str(uuid_mod.uuid4())
    source_id = str(row.id)
    uid, email = user.id, user.email
    indexer_service.enqueue(
        str(uid),
        source_id,
        email,
        lambda: run_analysis(task_id, tmp_path, uid, email, source_id),
    )
    payload = {"status": "started", "task_id": task_id}
    if mode:
        payload["mode"] = mode
    return payload


@router.post("/analyze")
async def analyze(  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
    batch_id: str | None = Form(None),  # noqa: B008
    background_tasks: BackgroundTasks = BackgroundTasks(),  # noqa: B008
    user=Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
):
    """테이크아웃 JSON 파일 업로드 → 백그라운드 분석 시작"""
    tmp_path = _temp_upload_path(file)
    content = await file.read()
    with open(tmp_path, "wb") as tmp:
        tmp.write(content)

    return await _start_upload_analysis(
        session=session,
        background_tasks=background_tasks,
        user=user,
        content=content,
        filename=file.filename,
        tmp_path=tmp_path,
        batch_id=batch_id,
    )


@router.post("/analyze/sample")
async def analyze_sample(  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
    batch_id: str | None = Form(None),  # noqa: B008
    background_tasks: BackgroundTasks = BackgroundTasks(),  # noqa: B008
    user=Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
):
    """샘플 모드 - 20개만 처리 (시연용)"""
    tmp_path = _temp_upload_path(file)
    content = await file.read()
    with open(tmp_path, "wb") as tmp:
        tmp.write(content)

    return await _start_upload_analysis(
        session=session,
        background_tasks=background_tasks,
        user=user,
        content=content,
        filename=file.filename,
        tmp_path=tmp_path,
        mode="sample",
        batch_id=batch_id,
    )


@router.post("/batch/{batch_id}/seal")
async def seal_batch_endpoint(
    batch_id: str,
    user=Depends(get_current_user_dep),  # noqa: B008
):
    """업로드 완료 후 '다 보냄' 신호 — 배치를 닫고 조건 되면 프로파일러 1회 트리거."""
    from app.services.analysis_source_service import seal_batch_async

    await seal_batch_async(user.id, batch_id, user.email)
    return {"status": "sealed"}


@router.get("/analyze/{task_id}")
def get_result(task_id: str):
    """분석 결과 조회"""
    if task_id not in analysis_status:
        return {"status": "not_found"}
    return analysis_status[task_id]


@router.get("/videos")
async def get_videos(
    session: AsyncSession = Depends(get_db), user=Depends(get_current_user_dep)
):
    """수집된 영상 목록 조회 (최신순, 본인 데이터만)"""
    from app.repositories.indexer_repository import get_all_catalog

    videos = await get_all_catalog(session, user_id=user.id)
    return [
        {
            "id": str(v.id),
            "title": v.title or "",
            "channel": v.channel,
            "url": v.url,
            "watched_at": str(v.watched_at) if v.watched_at else "",
            "youtube_category_id": v.youtube_category_id or "",
            "tags": v.tags if isinstance(v.tags, list) else [],
            "duration": v.duration_sec or 0,
            "is_shorts": v.is_shorts or False,
            "thumbnail_url": v.thumbnail_url or "",
        }
        for v in videos
    ]


@router.get("/graph-summary")
async def get_graph_summary(
    session: AsyncSession = Depends(get_db), user=Depends(get_current_user_dep)
):
    """시청 그래프 UI용 catalog 집계 (상위 카테고리·채널, 경량). 최근 2달 시청분만."""
    from app.agents.shared.analysis_window import WATCH_CATALOG_WINDOW_DAYS
    from app.repositories.indexer_repository import fetch_graph_summary

    return await fetch_graph_summary(
        session, user.id, window_days=WATCH_CATALOG_WINDOW_DAYS
    )


@router.get("/embedding-graph")
async def get_embedding_graph(
    before: str | None = None,
    after: str | None = None,
    snapshot_id: str | None = None,
    session: AsyncSession = Depends(get_db),
    user=Depends(get_current_user_dep),
):
    """영상별 임베딩 PCA 2D 투영 그래프.

    snapshot_id가 주어지고 그 스냅샷이 배치 소속이면 **그 배치 영상만** 투영한다.
    아니면 before/after 미지정 시 최근 2달(시청일 기준) 전체.
    """
    from datetime import datetime, timezone

    from app.agents.shared.analysis_window import WATCH_CATALOG_WINDOW_DAYS
    from app.repositories.indexer_repository import (
        fetch_catalog_embedding_rows,
        recent_watched_start,
    )
    from app.services.catalog_embedding_graph import build_embedding_graph_payload

    def _parse(s: str | None):
        if not s:
            return None
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    # 스냅샷의 배치 스코프 — 그 배치 소속 영상만 (시청일 윈도우는 적용 안 함:
    # 배치 데이터가 유저 최근 2달보다 과거일 수 있어 윈도우로 자르면 비어버림)
    if snapshot_id:
        import uuid as _uuid

        from app.repositories.analysis_source_repository import fetch_batch_source_ids
        from app.repositories.profiler_repository import fetch_profile_snapshot

        snap = await fetch_profile_snapshot(session, user.id, _uuid.UUID(snapshot_id))
        if snap is not None and snap.batch_id:
            source_ids = await fetch_batch_source_ids(session, snap.batch_id)
            rows = await fetch_catalog_embedding_rows(
                session, user.id, limit=2000, source_ids=source_ids
            )
            return build_embedding_graph_payload(rows)

    # after 미지정이면 '마지막 시청일 기준 2달'로 기본 필터
    parsed_after = _parse(after)
    if parsed_after is None:
        parsed_after = await recent_watched_start(
            session, user.id, WATCH_CATALOG_WINDOW_DAYS
        )

    # 그래프 과밀 방지 — 최근 2달 내에서도 최신 시청순 최대 2000개만
    rows = await fetch_catalog_embedding_rows(
        session, user.id, before=_parse(before), after=parsed_after, limit=2000
    )
    return build_embedding_graph_payload(rows)


@router.delete("/videos")
async def delete_all_videos(
    session: AsyncSession = Depends(get_db), user=Depends(get_current_user_dep)
):
    """본인 catalog + 분석 결과 + 구독 + 소스 이력 전체 삭제"""
    from app.repositories.analysis_source_repository import delete_sources_for_user
    from app.repositories.indexer_repository import (
        delete_subscriptions,
        delete_user_catalog,
    )

    await delete_user_catalog(session, user.id)
    await delete_subscriptions(session, user.id)
    await delete_sources_for_user(session, user.id)
    await session.commit()
    return {"message": "전체 삭제 완료"}


@router.get("/status")
def status():
    """인덱서 상태 확인"""
    return {"status": "running"}
