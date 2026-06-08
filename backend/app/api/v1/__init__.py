"""API v1 라우터 집합."""

from fastapi import APIRouter

from app.api.v1.trend import router as trend_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(
    trend_router,
    prefix="/trend",
    tags=["Trend Analysis"],
)
