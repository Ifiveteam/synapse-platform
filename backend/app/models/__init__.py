"""SQLAlchemy models."""

from app.models.analysis_batch import AnalysisBatch
from app.models.analysis_source_catalog import AnalysisSourceCatalog
from app.models.behavior import UserBehaviorLog
from app.models.chat import AIChatLog
from app.models.extension_auth_code import ExtensionAuthCode
from app.models.navigator_playlist import NavigatorPlaylist
from app.models.navigator_proposal_cache import NavigatorProposalCache
from app.models.scrap import Scrap
from app.models.scrap_embedding import ScrapEmbedding
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
    "ExtensionAuthCode",
    "NavigatorPlaylist",
    "NavigatorProposalCache",
    "Scrap",
    "ScrapEmbedding",
    "User",
    "UserBehaviorLog",
    "UserAnalysisSource",
    "UserIdealPersona",
    "UserProfileHistory",
    "UserSubscription",
    "UserToken",
    "UserWatchCatalog",
    "VideoAnalysis",
]
