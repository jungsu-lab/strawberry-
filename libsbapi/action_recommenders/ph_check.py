from __future__ import annotations

from libsbapi.action_recommenders.common import (
    RecommendationContext,
    RecommendationDraft,
    build_recommendation,
    first_available,
    usable_prediction,
)
from libsbapi.decision_contract import RecommendationResult


ACTION_TYPE = "ph_check"


def recommend(context: RecommendationContext) -> tuple[RecommendationResult, ...]:
    snapshot = context.snapshot
    ph = first_available(
        snapshot.root_zone_ph,
        snapshot.drainage_ph,
        snapshot.nutrient_state.feed_ph,
    )
    reasons: list[str] = []
    score = 0.14

    if ph is not None and not 5.5 <= ph <= 6.5:
        score += 0.44
        reasons.append("root-zone, drainage, or feed pH is outside the monitoring range")
    prediction = usable_prediction(context)
    if (
        prediction is not None
        and prediction.predicted_value is not None
        and not 5.5 <= prediction.predicted_value <= 6.5
        and not (ph is not None and not 5.5 <= ph <= 6.5)
    ):
        score += 0.34
        reasons.append("predicted pH drifts outside the monitoring range")

    return (
        build_recommendation(
            RecommendationDraft(
                action_type=ACTION_TYPE,
                score=score,
                reason=", ".join(reasons) or "pH signal is inside the starting monitoring range",
                expected_effect="support nutrient availability by confirming pH drift with calibrated sensors",
                risks=("pH correction should be gradual and based on repeated measurements",),
                evidence_rules=context.evidence_rules,
                prediction=context.prediction,
            )
        ),
    )
