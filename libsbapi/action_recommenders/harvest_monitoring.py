from __future__ import annotations

from libsbapi.action_recommenders.common import (
    RecommendationContext,
    RecommendationDraft,
    build_recommendation,
    usable_prediction,
)
from libsbapi.decision_contract import RecommendationResult


ACTION_TYPE = "harvest_monitoring"


def recommend(context: RecommendationContext) -> tuple[RecommendationResult, ...]:
    snapshot = context.snapshot
    reasons: list[str] = []
    score = 0.14

    if snapshot.growth_state.ripe_fruit_ratio is not None and snapshot.growth_state.ripe_fruit_ratio >= 0.65:
        score += 0.34
        reasons.append("ripe fruit ratio suggests harvest monitoring")
    if snapshot.growth_state.fruit_count is not None and snapshot.growth_state.fruit_count >= 30:
        score += 0.14
        reasons.append("visible fruit count supports harvest review")
    if snapshot.temperature_c is not None and snapshot.temperature_c >= 28.0:
        score += 0.1
        reasons.append("high temperature can increase quality-loss risk")
    prediction = usable_prediction(context)
    if (
        prediction is not None
        and prediction.target == "ripe_fruit_ratio"
        and prediction.predicted_value is not None
        and prediction.predicted_value >= 0.65
        and not (
            snapshot.growth_state.ripe_fruit_ratio is not None
            and snapshot.growth_state.ripe_fruit_ratio >= 0.65
        )
    ):
        score += 0.24
        reasons.append("predicted ripening enters the harvest monitoring range")

    return (
        build_recommendation(
            RecommendationDraft(
                action_type=ACTION_TYPE,
                score=score,
                reason=", ".join(reasons) or "harvest signal is weak; continue monitoring",
                expected_effect="support harvest timing review using ripening and quality-risk signals",
                risks=("market target and distribution temperature can change harvest thresholds",),
                evidence_rules=context.evidence_rules,
                prediction=context.prediction,
            )
        ),
    )
