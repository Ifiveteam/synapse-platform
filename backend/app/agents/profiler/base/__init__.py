"""Profiler domain models (Pydantic)."""

from app.agents.profiler.base.axes import (
    SYNAPSE_AXIS_KEYS,
    TASTE_DIVERSITY_AXES,
    AxesDelta,
    Synapse8Axes,
    SynapseAxisKey,
)
from app.agents.profiler.base.graph import GraphEdge, GraphNode, GraphViewData
from app.agents.profiler.base.insights import (
    AnomalyItem,
    IdealGap,
    IdealProfile,
    ProfileCompareDelta,
    ProfilerSnapshot,
)
from app.agents.profiler.base.job import (
    BehaviorEvent,
    BehaviorEventSummary,
    JobStatus,
    PersonaInfo,
)
from app.agents.profiler.base.layer_b import LayerB, LayerBDelta
from app.agents.profiler.base.profile import (
    BehaviorPatterns,
    ProfileInterpretation,
    ProfilerAnalysisOutput,
    ProfilerResult,
    Top5Interest,
)
from app.agents.profiler.base.record import (
    IndexedRecord,
    IndexedRecordsBundle,
    SourceType,
)
from app.services.email import DEFAULT_FROM_ADDRESS
from app.services.notification import (
    EmailChannel,
    InAppChannel,
    NotificationChannels,
    NotificationPayload,
)

__all__ = [
    "SYNAPSE_AXIS_KEYS",
    "TASTE_DIVERSITY_AXES",
    "AnomalyItem",
    "AxesDelta",
    "DEFAULT_FROM_ADDRESS",
    "BehaviorEvent",
    "BehaviorEventSummary",
    "BehaviorPatterns",
    "EmailChannel",
    "InAppChannel",
    "GraphEdge",
    "GraphNode",
    "GraphViewData",
    "IdealGap",
    "IdealProfile",
    "IndexedRecord",
    "IndexedRecordsBundle",
    "JobStatus",
    "LayerB",
    "LayerBDelta",
    "NotificationChannels",
    "NotificationPayload",
    "PersonaInfo",
    "ProfileCompareDelta",
    "ProfileInterpretation",
    "ProfilerAnalysisOutput",
    "ProfilerResult",
    "ProfilerSnapshot",
    "SourceType",
    "Synapse8Axes",
    "SynapseAxisKey",
    "Top5Interest",
]
