"""API v1 라우터 집합."""

from fastapi import APIRouter

from app.agents.profiler.api import router as profiler_router
from app.api.v1.indexer import router as indexer_router
from app.api.v1.trend import router as trend_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(indexer_router)
api_router.include_router(
    trend_router,
    prefix="/trend",
    tags=["Trend Analysis"],
)
api_router.include_router(profiler_router)
