"""API v1 라우터 집합."""

from fastapi import APIRouter

from app.api.v1.aggregator import router as aggregator_router
from app.api.v1.archiver import router as archiver_router
from app.api.v1.auth import router as auth_router
from app.api.v1.curator import router as curator_router
from app.api.v1.indexer import router as indexer_router
from app.api.v1.navigator import router as navigator_router
from app.api.v1.payment import router as payment_router
from app.api.v1.profiler import router as profiler_router
from app.api.v1.reporter import router as reporter_router
from app.api.v1.scrap import router as scrap_router
from app.api.v1.takeout import router as takeout_router
from app.api.v1.tracking import router as tracking_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(aggregator_router)
api_router.include_router(indexer_router)
api_router.include_router(auth_router)
api_router.include_router(takeout_router)
api_router.include_router(profiler_router)
api_router.include_router(navigator_router)
api_router.include_router(archiver_router)
api_router.include_router(scrap_router)
api_router.include_router(curator_router)
api_router.include_router(payment_router)
api_router.include_router(reporter_router)
api_router.include_router(tracking_router)
