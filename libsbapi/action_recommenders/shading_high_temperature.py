from __future__ import annotations

from libsbapi.action_recommenders.common import (
    RecommendationContext,
    RecommendationDraft,
    build_recommendation,
    usable_prediction,
)
from libsbapi.decision_contract import RecommendationResult


ACTION_TYPE = "shading_high_temperature"


def recommend(context: RecommendationContext) -> tuple[RecommendationResult, ...]:
    snapshot = context.snapshot
    reasons: list[str] = []
    score = 0.14

    if snapshot.temperature_c is not None and snapshot.temperature_c >= 28.0:
        score += 0.28
        reasons.append("temperature is in a high-temperature caution range")
    if snapshot.radiation_w_m2 is not None and snapshot.radiation_w_m2 >= 650.0:
        score += 0.22
        reasons.append("radiation is high")
    if snapshot.vpd_kpa is not None and snapshot.vpd_kpa >= 1.2:
        score += 0.16
        reasons.append("VPD is high")
    prediction = usable_prediction(context)
    if (
        prediction is not None
        and prediction.target == "temperature_c"
        and prediction.predicted_value is not None
        and prediction.predicted_value >= 28.0
        and not (snapshot.temperature_c is not None and snapshot.temperature_c >= 28.0)
    ):
        score += 0.24
        reasons.append("predicted temperature enters a high-temperature caution range")
    if (
        prediction is not None
        and prediction.target in {"radiation_w_m2", "cumulative_radiation_j_cm2"}
        and prediction.predicted_delta is not None
        and prediction.predicted_delta > 0.0
    ):
        score += 0.08
        reasons.append("GAM predicts rising radiation load")

    return (
        build_recommendation(
            RecommendationDraft(
                action_type=ACTION_TYPE,
                score=score,
                reason=", ".join(reasons) or "shading signal is weak",
                expected_effect="review heat-stress mitigation without reducing photosynthesis unnecessarily",
                risks=("excess shading can reduce photosynthesis and delay ripening",),
                evidence_rules=context.evidence_rules,
                prediction=context.prediction,
            )
        ),
    )
