"""API v1 라우터 집합."""

from fastapi import APIRouter

from app.api.v1.archiver import router as archiver_router
from app.api.v1.auth import router as auth_router
from app.api.v1.curator import router as curator_router
from app.api.v1.indexer import router as indexer_router
from app.api.v1.navigator import router as navigator_router
from app.api.v1.payment import router as payment_router
from app.api.v1.profiler import router as profiler_router
from app.api.v1.takeout import router as takeout_router
from app.api.v1.trend import router as trend_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(indexer_router)
api_router.include_router(auth_router)
api_router.include_router(takeout_router)
api_router.include_router(
    trend_router,
    prefix="/trend",
    tags=["Trend Analysis"],
)
api_router.include_router(profiler_router)
api_router.include_router(navigator_router)
api_router.include_router(archiver_router)
api_router.include_router(curator_router)
api_router.include_router(payment_router)
