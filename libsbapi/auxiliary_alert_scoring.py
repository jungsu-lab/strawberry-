from __future__ import annotations

from .decision_contract import CurrentGreenhouseState, WorkNeedScore


def auxiliary_alert_scores(
    state: CurrentGreenhouseState,
    context_payload: dict | None = None,
    *,
    minimum_score: float = 35.0,
) -> tuple[WorkNeedScore, ...]:
    """Prototype Level 2 alert scores for offline decision-support demos.

    These are environmental/image proxy alerts only. They are not validated
    disease, harvest, or leaf-removal predictions.
    """

    payload = context_payload or {}
    scores = (
        _disease_alert_score(state, payload),
        _harvest_alert_score(state, payload),
        _leaf_alert_score(state, payload),
    )
    return tuple(score for score in scores if score.score >= minimum_score)


def _disease_alert_score(state: CurrentGreenhouseState, context_payload: dict) -> WorkNeedScore:
    image = _image_payload(context_payload)
    score = 0.0
    if state.humidity is not None and state.humidity >= 85.0:
        score += 36.0
    if state.vpd is not None and state.vpd <= 0.35:
        score += 28.0
    if image.get("disease_spot_ratio") is not None:
        score += 14.0
    return _aux_score(
        "disease_environment_risk_proxy",
        min(score, 88.0),
        disease_environment_risk=min(score, 88.0),
    )


def _harvest_alert_score(state: CurrentGreenhouseState, context_payload: dict) -> WorkNeedScore:
    image = _image_payload(context_payload)
    score = 0.0
    if state.growth_stage in {"fruiting", "harvest"}:
        score += 36.0
    if image.get("ripe_fruit_ratio") is not None:
        score += 28.0
    if image.get("fruit_count") is not None:
        score += 14.0
    return _aux_score("harvest_monitoring", min(score, 82.0))


def _leaf_alert_score(state: CurrentGreenhouseState, context_payload: dict) -> WorkNeedScore:
    image = _image_payload(context_payload)
    score = 0.0
    if image.get("leaf_density") is not None:
        score += 34.0
    if state.humidity is not None and state.humidity >= 85.0:
        score += 18.0
    return _aux_score("leaf_removal_caution", min(score, 70.0), disease_environment_risk=min(score, 70.0))


def _aux_score(action_type: str, score: float, **components: float) -> WorkNeedScore:
    return WorkNeedScore(
        action_type=action_type,
        score=score,
        priority_rank=10,
        moisture_stress=components.get("moisture_stress", 0.0),
        salinity_stress=components.get("salinity_stress", 0.0),
        high_temp_stress=components.get("high_temp_stress", 0.0),
        low_temp_stress=components.get("low_temp_stress", 0.0),
        disease_environment_risk=components.get("disease_environment_risk", 0.0),
        energy_cost=components.get("energy_cost", 0.0),
        confidence=0.42,
        requires_human_review=True,
    )


def _image_payload(context_payload: dict) -> dict:
    snapshot = context_payload.get("snapshot")
    if not isinstance(snapshot, dict):
        return {}
    image = snapshot.get("image")
    return image if isinstance(image, dict) else {}
