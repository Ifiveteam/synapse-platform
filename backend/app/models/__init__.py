"""SQLAlchemy models."""

from app.models.analysis_batch import AnalysisBatch
from app.models.analysis_source_catalog import AnalysisSourceCatalog
from app.models.b2b_trend_report import B2BReportAudience, B2BTrendReport
from app.models.behavior import UserBehaviorLog
from app.models.chat import AIChatLog
from app.models.extension_auth_code import ExtensionAuthCode
from app.models.global_trends_snapshot import GlobalTrendsSnapshot
from app.models.knowledge_graph import KnowledgeGraph
from app.models.navigator_playlist import NavigatorPlaylist
from app.models.navigator_proposal_cache import NavigatorProposalCache
from app.models.scrap import Scrap
from app.models.scrap_embedding import ScrapEmbedding
from app.models.trend_domain import (
    TREND_DOMAIN_VALUES,
    TrendDomain,
    trend_domain_pg_enum,
)
from app.models.trend_keyword_embedding import TrendKeywordEmbedding
from app.models.user import User
from app.models.user_analysis_source import UserAnalysisSource
from app.models.user_ideal_persona import UserIdealPersona
from app.models.user_profile_history import UserProfileHistory
from app.models.user_subscription import UserSubscription
from app.models.user_token import UserToken
from app.models.user_watch_catalog import UserWatchCatalog
from app.models.video_analysis import VideoAnalysis

__all__ = [
    "AIChatLog",
    "AnalysisBatch",
    "AnalysisSourceCatalog",
    "B2BReportAudience",
    "B2BTrendReport",
    "ExtensionAuthCode",
    "GlobalTrendsSnapshot",
    "KnowledgeGraph",
    "NavigatorPlaylist",
    "NavigatorProposalCache",
    "Scrap",
    "ScrapEmbedding",
    "TREND_DOMAIN_VALUES",
    "TrendDomain",
    "TrendKeywordEmbedding",
    "User",
    "UserBehaviorLog",
    "UserAnalysisSource",
    "UserIdealPersona",
    "UserProfileHistory",
    "UserSubscription",
    "UserToken",
    "UserWatchCatalog",
    "VideoAnalysis",
    "trend_domain_pg_enum",
]
