from __future__ import annotations

from libsbapi.action_recommenders.common import (
    RecommendationContext,
    RecommendationDraft,
    build_recommendation,
    usable_prediction,
)
from libsbapi.decision_contract import RecommendationResult


ACTION_TYPE = "ventilation_dehumidification"


def recommend(context: RecommendationContext) -> tuple[RecommendationResult, ...]:
    snapshot = context.snapshot
    reasons: list[str] = []
    score = 0.18

    if snapshot.humidity_pct is not None and snapshot.humidity_pct >= 85.0:
        score += 0.32
        reasons.append("humidity is high")
    if snapshot.vpd_kpa is not None and snapshot.vpd_kpa <= 0.35:
        score += 0.26
        reasons.append("low VPD suggests wet-canopy conditions")
    prediction = usable_prediction(context)
    if (
        prediction is not None
        and prediction.target == "humidity_pct"
        and prediction.predicted_value is not None
        and prediction.predicted_value >= 85.0
        and not (snapshot.humidity_pct is not None and snapshot.humidity_pct >= 85.0)
    ):
        score += 0.32
        reasons.append("predicted humidity remains above the dehumidification threshold")
    if (
        prediction is not None
        and prediction.target == "vpd_kpa"
        and prediction.predicted_value is not None
        and prediction.predicted_value <= 0.35
        and not (snapshot.vpd_kpa is not None and snapshot.vpd_kpa <= 0.35)
    ):
        score += 0.26
        reasons.append("predicted VPD remains in a low wet-canopy range")

    return (
        build_recommendation(
            RecommendationDraft(
                action_type=ACTION_TYPE,
                score=score,
                reason=", ".join(reasons) or "ventilation/dehumidification signal is weak",
                expected_effect="reduce humidity and canopy wetness conditions while staying in decision-support mode",
                risks=("human review is required before ventilation or dehumidification control changes",),
                evidence_rules=context.evidence_rules,
                prediction=context.prediction,
            )
        ),
    )
