from __future__ import annotations

from libsbapi.action_recommenders.common import (
    RecommendationContext,
    RecommendationDraft,
    build_recommendation,
    usable_prediction,
)
from libsbapi.decision_contract import RecommendationResult


ACTION_TYPE = "disease_environment_risk_proxy"


def recommend(context: RecommendationContext) -> tuple[RecommendationResult, ...]:
    snapshot = context.snapshot
    reasons = ["environmental disease risk proxy review"]
    score = 0.16

    if snapshot.humidity_pct is not None and snapshot.humidity_pct >= 85.0:
        score += 0.28
        reasons.append("humidity is high")
    if snapshot.vpd_kpa is not None and snapshot.vpd_kpa <= 0.35:
        score += 0.22
        reasons.append("VPD is low")
    if snapshot.weather_state.rain_probability_pct is not None and snapshot.weather_state.rain_probability_pct >= 60.0:
        score += 0.16
        reasons.append("rain probability increases monitoring attention")
    if snapshot.growth_state.disease_spot_ratio is not None and snapshot.growth_state.disease_spot_ratio >= 0.03:
        score += 0.18
        reasons.append("visible disease proxy requires field confirmation")
    prediction = usable_prediction(context)
    if (
        prediction is not None
        and prediction.target == "humidity_pct"
        and prediction.predicted_value is not None
        and prediction.predicted_value >= 85.0
        and not (snapshot.humidity_pct is not None and snapshot.humidity_pct >= 85.0)
    ):
        score += 0.2
        reasons.append("predicted humidity keeps environmental disease-risk proxy elevated")
    if (
        prediction is not None
        and prediction.target == "vpd_kpa"
        and prediction.predicted_value is not None
        and prediction.predicted_value <= 0.35
        and not (snapshot.vpd_kpa is not None and snapshot.vpd_kpa <= 0.35)
    ):
        score += 0.16
        reasons.append("predicted VPD keeps wet-canopy proxy elevated")

    return (
        build_recommendation(
            RecommendationDraft(
                action_type=ACTION_TYPE,
                score=score,
                reason=", ".join(reasons),
                expected_effect="prioritize scouting and preventive review without claiming disease prediction",
                risks=("not actual disease prediction without disease labels",),
                evidence_rules=context.evidence_rules,
                safety_flags=(
                    "decision_support_only",
                    "requires_human_review",
                    "requires_field_confirmation",
                ),
                prediction=context.prediction,
            )
        ),
    )
