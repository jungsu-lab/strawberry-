from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

from .decision_contract import CurrentGreenhouseState, PredictionResult, WorkNeedScore
from .evidence_rules import EvidenceRule, core_level1_rules, evidence_rules_by_action_type
from .prediction_confidence import gate_prediction_result
from .prediction_targets import prediction_relates_to_action


LEVEL1_ACTIONS: Final = (
    "irrigation",
    "nutrient_ec_check",
    "ventilation_dehumidification",
    "shading_high_temperature",
    "heating_low_temperature",
)
PRIORITY_ORDER: Final = {
    "irrigation": 1,
    "nutrient_ec_check": 2,
    "ventilation_dehumidification": 3,
    "shading_high_temperature": 4,
    "heating_low_temperature": 5,
}


@dataclass(frozen=True, slots=True)
class WorkNeedScorer:
    evidence_rules: tuple[EvidenceRule, ...]

    def score(
        self,
        current_state: CurrentGreenhouseState,
        predictions: tuple[PredictionResult, ...] = (),
        scenario_refs: tuple[str, ...] = (),
    ) -> tuple[WorkNeedScore, ...]:
        del scenario_refs
        rules_by_action = evidence_rules_by_action_type(core_level1_rules(self.evidence_rules))
        scores = tuple(
            self._score_action(action_type, current_state, predictions, rules_by_action.get(action_type, ()))
            for action_type in LEVEL1_ACTIONS
        )
        return tuple(sorted(scores, key=lambda item: (item.score, -item.priority_rank), reverse=True))

    def _score_action(
        self,
        action_type: str,
        state: CurrentGreenhouseState,
        predictions: tuple[PredictionResult, ...],
        rules: tuple[EvidenceRule, ...],
    ) -> WorkNeedScore:
        usable_predictions = _usable_predictions(action_type, predictions)
        missing_penalty = _missing_data_penalty(state, action_type)
        if action_type == "irrigation":
            score = _irrigation_score(state, usable_predictions)
        elif action_type == "nutrient_ec_check":
            score = _nutrient_score(state, usable_predictions)
        elif action_type == "ventilation_dehumidification":
            score = _ventilation_score(state, usable_predictions)
        elif action_type == "shading_high_temperature":
            score = _shading_score(state, usable_predictions)
        elif action_type == "heating_low_temperature":
            score = _heating_score(state, usable_predictions)
        else:
            raise ValueError(f"unsupported Level 1 action: {action_type}")

        score = replace(score, score=_clamp100(score.score - missing_penalty))
        confidence = _confidence(state, action_type, usable_predictions, rules)
        return replace(
            score,
            confidence=confidence,
            requires_human_review=True,
        )


def _irrigation_score(
    state: CurrentGreenhouseState,
    predictions: tuple[PredictionResult, ...],
) -> WorkNeedScore:
    moisture = _first_prediction_value(predictions, {"root_zone_moisture", "substrate_moisture"}) 
    if moisture is None:
        moisture = state.root_zone_moisture
    vpd = _first_prediction_value(predictions, {"vpd"}) if _has_prediction(predictions, "vpd") else state.vpd
    radiation = (
        _first_prediction_value(predictions, {"solar_radiation"})
        if _has_prediction(predictions, "solar_radiation")
        else state.solar_radiation
    )
    moisture_delta = _first_prediction_delta(predictions, {"root_zone_moisture", "substrate_moisture"})
    moisture_stress = 0.0
    if moisture is not None:
        if moisture < 45.0:
            moisture_stress += 76.0
        elif moisture < 55.0:
            moisture_stress += 56.0
        elif moisture < 60.0:
            moisture_stress += 34.0
    if vpd is not None and vpd >= 1.2:
        moisture_stress += 16.0
    if radiation is not None and radiation >= 650.0:
        moisture_stress += 12.0
    if moisture_delta is not None and moisture_delta <= -3.0:
        moisture_stress += 10.0
    score = _clamp100(moisture_stress)
    return _work_score("irrigation", score, moisture_stress=_clamp100(moisture_stress))


def _nutrient_score(
    state: CurrentGreenhouseState,
    predictions: tuple[PredictionResult, ...],
) -> WorkNeedScore:
    ec = _first_prediction_value(predictions, {"root_ec", "drain_ec", "feed_ec"})
    if ec is None:
        ec = _first_not_none(state.root_ec, state.drain_ec, state.feed_ec)
    salinity = 0.0
    if ec is not None:
        if ec >= 2.6:
            salinity += 78.0
        elif ec >= 2.2:
            salinity += 66.0
        elif ec < 0.8:
            salinity += 46.0
    score = _clamp100(salinity)
    return _work_score("nutrient_ec_check", score, salinity_stress=_clamp100(salinity))


def _ventilation_score(
    state: CurrentGreenhouseState,
    predictions: tuple[PredictionResult, ...],
) -> WorkNeedScore:
    humidity = _first_prediction_value(predictions, {"humidity"}) if _has_prediction(predictions, "humidity") else state.humidity
    vpd = _first_prediction_value(predictions, {"vpd"}) if _has_prediction(predictions, "vpd") else state.vpd
    risk = 0.0
    if humidity is not None and humidity >= 90.0:
        risk += 48.0
    elif humidity is not None and humidity >= 85.0:
        risk += 36.0
    if vpd is not None and vpd <= 0.35:
        risk += 34.0
    score = _clamp100(risk)
    return _work_score("ventilation_dehumidification", score, disease_environment_risk=_clamp100(risk))


def _shading_score(
    state: CurrentGreenhouseState,
    predictions: tuple[PredictionResult, ...],
) -> WorkNeedScore:
    temperature = _first_prediction_value(predictions, {"air_temp"}) if _has_prediction(predictions, "air_temp") else state.air_temp
    radiation = (
        _first_prediction_value(predictions, {"solar_radiation"})
        if _has_prediction(predictions, "solar_radiation")
        else state.solar_radiation
    )
    vpd = _first_prediction_value(predictions, {"vpd"}) if _has_prediction(predictions, "vpd") else state.vpd
    stress = 0.0
    if temperature is not None and temperature >= 30.0:
        stress += 52.0
    elif temperature is not None and temperature >= 28.0:
        stress += 42.0
    if radiation is not None and radiation >= 650.0:
        stress += 22.0
    if vpd is not None and vpd >= 1.2:
        stress += 18.0
    score = _clamp100(stress)
    return _work_score("shading_high_temperature", score, high_temp_stress=_clamp100(stress))


def _heating_score(
    state: CurrentGreenhouseState,
    predictions: tuple[PredictionResult, ...],
) -> WorkNeedScore:
    temperature = _first_prediction_value(predictions, {"air_temp"}) if _has_prediction(predictions, "air_temp") else state.air_temp
    stress = 0.0
    if temperature is not None and temperature <= 10.0:
        stress += 72.0
    elif temperature is not None and temperature <= 13.0:
        stress += 56.0
    if state.outside_temp is not None and state.outside_temp <= 3.0:
        stress += 10.0
    if state.time_of_day in {"night", "evening"} and temperature is not None and temperature <= 13.0:
        stress += 8.0
    energy_cost = 18.0 if stress >= 60.0 else 8.0 if stress > 0.0 else 0.0
    score = _clamp100(stress)
    return _work_score(
        "heating_low_temperature",
        score,
        low_temp_stress=_clamp100(stress),
        energy_cost=energy_cost,
    )


def _work_score(action_type: str, score: float, **components: float) -> WorkNeedScore:
    return WorkNeedScore(
        action_type=action_type,
        score=_clamp100(score),
        priority_rank=PRIORITY_ORDER[action_type],
        moisture_stress=components.get("moisture_stress", 0.0),
        salinity_stress=components.get("salinity_stress", 0.0),
        high_temp_stress=components.get("high_temp_stress", 0.0),
        low_temp_stress=components.get("low_temp_stress", 0.0),
        disease_environment_risk=components.get("disease_environment_risk", 0.0),
        energy_cost=components.get("energy_cost", 0.0),
        confidence=0.5,
        requires_human_review=True,
    )


def _usable_predictions(
    action_type: str,
    predictions: tuple[PredictionResult, ...],
) -> tuple[PredictionResult, ...]:
    usable: list[PredictionResult] = []
    for prediction in predictions:
        if not prediction_relates_to_action(action_type, prediction):
            continue
        if gate_prediction_result(prediction).use_model:
            usable.append(prediction)
    return tuple(usable)


def _confidence(
    state: CurrentGreenhouseState,
    action_type: str,
    predictions: tuple[PredictionResult, ...],
    rules: tuple[EvidenceRule, ...],
) -> float:
    base = 0.56 if rules else 0.42
    if predictions:
        base += 0.12
    base -= _missing_data_penalty(state, action_type) / 200.0
    return round(max(0.2, min(base, 0.82)), 3)


def _missing_data_penalty(state: CurrentGreenhouseState, action_type: str) -> float:
    required = {
        "irrigation": ("root_zone_moisture",),
        "nutrient_ec_check": ("drain_ec", "root_ec", "feed_ec"),
        "ventilation_dehumidification": ("humidity", "vpd"),
        "shading_high_temperature": ("air_temp", "solar_radiation", "vpd"),
        "heating_low_temperature": ("air_temp",),
    }[action_type]
    if action_type == "nutrient_ec_check":
        return 8.0 if all(getattr(state, field) is None for field in required) else 0.0
    missing = sum(1 for field in required if getattr(state, field) is None)
    return min(missing * 6.0, 18.0)


def _first_prediction_value(
    predictions: tuple[PredictionResult, ...],
    targets: set[str],
) -> float | None:
    values = [item.predicted_value for item in predictions if item.target in targets and item.predicted_value is not None]
    return values[0] if values else None


def _first_prediction_delta(
    predictions: tuple[PredictionResult, ...],
    targets: set[str],
) -> float | None:
    values = [item.predicted_delta for item in predictions if item.target in targets and item.predicted_delta is not None]
    return values[0] if values else None


def _has_prediction(predictions: tuple[PredictionResult, ...], target: str) -> bool:
    return any(item.target == target for item in predictions)


def _first_not_none(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return value
    return None


def _clamp100(value: float) -> float:
    return round(max(0.0, min(value, 100.0)), 3)
