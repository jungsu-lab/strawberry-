from __future__ import annotations

from libsbapi.action_recommenders.common import (
    RecommendationContext,
    RecommendationDraft,
    build_recommendation,
    usable_prediction,
)
from libsbapi.decision_contract import RecommendationResult


ACTION_TYPE = "heating_low_temperature"


def recommend(context: RecommendationContext) -> tuple[RecommendationResult, ...]:
    snapshot = context.snapshot
    reasons: list[str] = []
    score = 0.12

    if snapshot.temperature_c is not None and snapshot.temperature_c <= 13.0:
        score += 0.42
        reasons.append("low temperature may slow strawberry growth")
    if snapshot.temperature_c is not None and snapshot.temperature_c <= 10.0:
        score += 0.18
        reasons.append("low temperature is near a stronger thermal protection trigger")
    if snapshot.weather_state.outside_temperature_c is not None and snapshot.weather_state.outside_temperature_c <= 3.0:
        score += 0.12
        reasons.append("outside temperature raises heat-retention attention")
    prediction = usable_prediction(context)
    if (
        prediction is not None
        and prediction.target in {"temperature_c", "outside_temperature_c"}
        and prediction.predicted_value is not None
        and prediction.predicted_value <= 13.0
        and not (snapshot.temperature_c is not None and snapshot.temperature_c <= 13.0)
    ):
        score += 0.34
        reasons.append("predicted temperature enters a low-temperature caution range")

    return (
        build_recommendation(
            RecommendationDraft(
                action_type=ACTION_TYPE,
                score=score,
                reason=", ".join(reasons) or "heating signal is weak",
                expected_effect="review heating or thermal protection for flowering, fruiting, and ripening stability",
                risks=("consider energy cost and humidity rise when vents are closed",),
                evidence_rules=context.evidence_rules,
                prediction=context.prediction,
            )
        ),
    )
