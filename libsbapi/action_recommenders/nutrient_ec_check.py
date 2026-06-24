from __future__ import annotations

from libsbapi.action_recommenders.common import (
    RecommendationContext,
    RecommendationDraft,
    build_recommendation,
    first_available,
    usable_prediction,
)
from libsbapi.decision_contract import RecommendationResult


ACTION_TYPE = "nutrient_ec_check"


def recommend(context: RecommendationContext) -> tuple[RecommendationResult, ...]:
    snapshot = context.snapshot
    zone_ec = first_available(snapshot.root_zone_ec, snapshot.drainage_ec)
    reasons: list[str] = []
    score = 0.16

    if zone_ec is not None and zone_ec >= 2.2:
        score += 0.48
        reasons.append("root-zone or drainage EC is high")
    if snapshot.nutrient_state.feed_ec is not None and snapshot.nutrient_state.feed_ec > 1.5:
        score += 0.2
        reasons.append("feed EC is above the starting Seolhyang range")
    if snapshot.nutrient_state.feed_ec is not None and snapshot.nutrient_state.feed_ec < 0.8:
        score += 0.16
        reasons.append("feed EC is below the starting Seolhyang range")
    if snapshot.root_zone_ec is not None and snapshot.drainage_ec is not None:
        reasons.append("compare root-zone EC with drainage EC before changing fertigation")
    prediction = usable_prediction(context)
    if (
        prediction is not None
        and prediction.predicted_value is not None
        and prediction.predicted_value >= 2.2
        and not (zone_ec is not None and zone_ec >= 2.2)
    ):
        score += 0.4
        reasons.append("predicted EC enters a high monitoring range")

    return (
        build_recommendation(
            RecommendationDraft(
                action_type=ACTION_TYPE,
                score=score,
                reason=", ".join(reasons) or "EC signal is inside the starting monitoring range",
                expected_effect="check salinity accumulation or nutrient dilution before adjusting fertilizer strength",
                risks=("do not diagnose plant nutrient status from EC alone",),
                evidence_rules=context.evidence_rules,
                prediction=context.prediction,
            )
        ),
    )
