from __future__ import annotations

from libsbapi.action_recommenders.common import (
    RecommendationContext,
    RecommendationDraft,
    build_recommendation,
    has_recent_work,
    usable_prediction,
)
from libsbapi.decision_contract import RecommendationResult


ACTION_TYPE = "leaf_removal_caution"


def recommend(context: RecommendationContext) -> tuple[RecommendationResult, ...]:
    snapshot = context.snapshot
    reasons = ["cautious leaf removal review only"]
    risks = ["avoid aggressive or repeated leaf removal that reduces plant vigor"]
    score = 0.14

    if snapshot.growth_state.leaf_density is not None and snapshot.growth_state.leaf_density >= 0.8:
        score += 0.28
        reasons.append("leaf density is high")
    if snapshot.humidity_pct is not None and snapshot.humidity_pct >= 85.0:
        score += 0.12
        reasons.append("humidity suggests airflow review")
    if has_recent_work(context, "leaf_pruning"):
        score -= 0.2
        risks.append("recent leaf pruning should lower urgency")
    prediction = usable_prediction(context)
    if (
        prediction is not None
        and prediction.target == "leaf_density"
        and prediction.predicted_value is not None
        and prediction.predicted_value >= 0.8
        and not (
            snapshot.growth_state.leaf_density is not None
            and snapshot.growth_state.leaf_density >= 0.8
        )
    ):
        score += 0.16
        reasons.append("predicted leaf density supports conservative canopy review")

    return (
        build_recommendation(
            RecommendationDraft(
                action_type=ACTION_TYPE,
                score=min(score, 0.62),
                reason=", ".join(reasons),
                expected_effect="improve canopy airflow only after confirming plant vigor and leaf area",
                risks=tuple(risks),
                evidence_rules=context.evidence_rules,
                prediction=context.prediction,
            )
        ),
    )
