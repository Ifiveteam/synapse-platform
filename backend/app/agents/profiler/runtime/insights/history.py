"""Snapshot compare delta and anomaly detection."""

from __future__ import annotations

from app.agents.profiler.base import (
    SYNAPSE_AXIS_KEYS,
    AnomalyItem,
    AxesDelta,
    LayerBDelta,
    ProfileCompareDelta,
    ProfilerResult,
    ProfilerSnapshot,
)


def _axes_delta(before: ProfilerResult, after: ProfilerResult) -> AxesDelta:
    values = {
        key: float(getattr(after.axes, key)) - float(getattr(before.axes, key))
        for key in SYNAPSE_AXIS_KEYS
    }
    return AxesDelta(**values)


def _layer_b_delta(before: ProfilerResult, after: ProfilerResult) -> LayerBDelta:
    return LayerBDelta(
        search_active_ratio=round(
            after.layer_b.search_active_ratio - before.layer_b.search_active_ratio,
            3,
        ),
        viewing_concentration=round(
            after.layer_b.viewing_concentration - before.layer_b.viewing_concentration,
            3,
        ),
        taste_diversity_index=round(
            after.layer_b.taste_diversity_index - before.layer_b.taste_diversity_index,
            1,
        ),
        exploration_depth=round(
            after.layer_b.exploration_depth - before.layer_b.exploration_depth,
            3,
        ),
    )


def compute_compare_delta(
    user_id: str,
    from_snapshot: ProfilerSnapshot,
    to_snapshot: ProfilerSnapshot,
) -> ProfileCompareDelta:
    before = from_snapshot.result
    after = to_snapshot.result
    before_labels = {item.label for item in before.top5_interests}
    after_labels = {item.label for item in after.top5_interests}
    return ProfileCompareDelta(
        user_id=user_id,
        from_version=from_snapshot.version,
        to_version=to_snapshot.version,
        axes_delta=_axes_delta(before, after),
        layer_b_delta=_layer_b_delta(before, after),
        top5_added=sorted(after_labels - before_labels),
        top5_removed=sorted(before_labels - after_labels),
    )


def detect_anomalies(delta: ProfileCompareDelta) -> list[AnomalyItem]:
    anomalies: list[AnomalyItem] = []
    layer_b = delta.layer_b_delta

    if abs(layer_b.viewing_concentration) >= 0.15:
        direction = "증가" if layer_b.viewing_concentration > 0 else "감소"
        shift = abs(layer_b.viewing_concentration)
        anomalies.append(
            AnomalyItem(
                code="viewing_concentration_shift",
                message=(f"채널 편중도가 {shift:.0%}p {direction}했습니다."),
                severity="warning"
                if abs(layer_b.viewing_concentration) < 0.25
                else "alert",
            )
        )

    if abs(layer_b.exploration_depth) >= 0.2:
        anomalies.append(
            AnomalyItem(
                code="exploration_depth_shift",
                message=(f"탐색 깊이 변화: {layer_b.exploration_depth:+.0%}p"),
                severity="info",
            )
        )

    for key in SYNAPSE_AXIS_KEYS:
        change = float(getattr(delta.axes_delta, key))
        if abs(change) >= 15:
            anomalies.append(
                AnomalyItem(
                    code=f"axis_shift_{key}",
                    message=f"{key} 축이 {change:+.0f}점 변동했습니다.",
                    severity="info",
                )
            )

    return anomalies
