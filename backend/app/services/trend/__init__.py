"""트렌드 분석 게시판·PDF 서비스."""

from app.services.trend.mapper import (
    require_report_from_state,
    state_to_trend_post,
    to_post_response,
    to_post_summary,
)
from app.services.trend.pdf import build_trend_report_pdf, trend_report_pdf_filename
from app.services.trend.repository import get_post, list_posts, save_post
from app.services.trend.types import TrendPostRecord

__all__ = [
    "TrendPostRecord",
    "build_trend_report_pdf",
    "get_post",
    "list_posts",
    "require_report_from_state",
    "save_post",
    "state_to_trend_post",
    "to_post_response",
    "to_post_summary",
    "trend_report_pdf_filename",
]
