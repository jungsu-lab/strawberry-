from __future__ import annotations

from libsbapi.action_recommenders.common import (
    RecommendationContext,
    RecommendationDraft,
    build_recommendation,
    has_recent_work,
    usable_prediction,
)
from libsbapi.decision_contract import RecommendationResult


ACTION_TYPE = "irrigation"


def recommend(context: RecommendationContext) -> tuple[RecommendationResult, ...]:
    snapshot = context.snapshot
    reasons: list[str] = []
    risks = ["confirm recent irrigation, drainage, and sensor units before changing volume"]
    score = 0.18

    if snapshot.substrate_moisture_pct is not None and snapshot.substrate_moisture_pct < 60.0:
        score += 0.34
        reasons.append("substrate moisture is below the literature starting threshold")
    if snapshot.vpd_kpa is not None and snapshot.vpd_kpa >= 1.2:
        score += 0.22
        reasons.append("VPD is high, indicating higher transpiration demand")
    if snapshot.radiation_w_m2 is not None and snapshot.radiation_w_m2 >= 650.0:
        score += 0.12
        reasons.append("radiation is high enough to raise water-demand attention")
    prediction = usable_prediction(context)
    if (
        prediction is not None
        and prediction.predicted_value is not None
        and prediction.predicted_value < 60.0
        and not (
            snapshot.substrate_moisture_pct is not None
            and snapshot.substrate_moisture_pct < 60.0
        )
    ):
        score += 0.34
        reasons.append("predicted substrate moisture falls below the literature starting threshold")
    if (
        prediction is not None
        and prediction.predicted_delta is not None
        and prediction.predicted_delta <= -3.0
        and snapshot.vpd_kpa is not None
        and snapshot.vpd_kpa >= 1.2
    ):
        score += 0.08
        reasons.append("GAM predicts moisture decline while VPD is high")
    if has_recent_work(context, ACTION_TYPE):
        score -= 0.16
        risks.append("recent irrigation history should reduce urgency until response is checked")

    return (
        build_recommendation(
            RecommendationDraft(
                action_type=ACTION_TYPE,
                score=score,
                reason=", ".join(reasons) or "irrigation signal is weak; monitor substrate moisture",
                expected_effect="maintain root-zone water supply without treating the output as a control command",
                risks=tuple(risks),
                evidence_rules=context.evidence_rules,
                prediction=context.prediction,
            )
        ),
    )
