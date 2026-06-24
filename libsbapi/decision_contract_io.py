from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

from .decision_contract import (
    ACTION_TYPES,
    PRIORITIES,
    ActionCandidate,
    ActionType,
    DecisionContractError,
    DecisionContractSample,
    EvidenceReference,
    GreenhouseSnapshot,
    GrowthState,
    NutrientState,
    PredictionResult,
    Priority,
    RecommendationResult,
    RootZoneState,
    SensorState,
    WeatherState,
    WorkHistoryEvent,
)


JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


def load_decision_contract_sample(path: Path) -> DecisionContractSample:
    with path.open(encoding="utf-8") as file:
        payload: JsonValue = json.load(file)
    return decision_contract_sample_from_json(_json_object(payload, "root"))


def decision_contract_sample_from_json(data: JsonObject) -> DecisionContractSample:
    return DecisionContractSample(
        snapshot=greenhouse_snapshot_from_json(_object_field(data, "snapshot")),
        action_candidates=tuple(
            action_candidate_from_json(item)
            for item in _object_list_field(data, "action_candidates")
        ),
        predictions=tuple(
            prediction_result_from_json(item)
            for item in _object_list_field(data, "predictions")
        ),
        recommendation=recommendation_result_from_json(_object_field(data, "recommendation")),
    )


def greenhouse_snapshot_from_json(data: JsonObject) -> GreenhouseSnapshot:
    return GreenhouseSnapshot(
        timestamp=_required_str(data, "timestamp"),
        sensor_state=SensorState(
            temperature_c=_float_field(data, "temperature_c"),
            humidity_pct=_float_field(data, "humidity_pct"),
            vpd_kpa=_float_field(data, "vpd_kpa"),
            radiation_w_m2=_float_field(data, "radiation_w_m2"),
            cumulative_radiation_j_cm2=_float_field(data, "cumulative_radiation_j_cm2"),
            co2_ppm=_float_field(data, "co2_ppm"),
        ),
        root_zone_state=RootZoneState(
            substrate_moisture_pct=_float_field(data, "substrate_moisture_pct"),
            root_zone_ec=_float_field(data, "root_zone_ec"),
            root_zone_ph=_float_field(data, "root_zone_ph"),
        ),
        nutrient_state=NutrientState(
            drainage_ec=_float_field(data, "drainage_ec"),
            drainage_ph=_float_field(data, "drainage_ph"),
            feed_ec=_float_field(data, "feed_ec"),
            feed_ph=_float_field(data, "feed_ph"),
            drainage_ratio_pct=_float_field(data, "drainage_ratio_pct"),
        ),
        weather_state=weather_state_from_json(_object_field(data, "weather_state", required=False)),
        growth_state=growth_state_from_json(_object_field(data, "growth_state", required=False)),
        recent_work_history=tuple(
            work_history_event_from_json(item)
            for item in _object_list_field(data, "recent_work_history")
        ),
    )


def weather_state_from_json(data: JsonObject) -> WeatherState:
    return WeatherState(
        rain_probability_pct=_float_field(data, "rain_probability_pct"),
        expected_rain_mm=_float_field(data, "expected_rain_mm"),
        outside_temperature_c=_float_field(data, "outside_temperature_c"),
        outside_humidity_pct=_float_field(data, "outside_humidity_pct"),
    )


def growth_state_from_json(data: JsonObject) -> GrowthState:
    return GrowthState(
        growth_stage=_optional_str(data, "growth_stage"),
        fruit_count=_int_field(data, "fruit_count"),
        ripe_fruit_ratio=_float_field(data, "ripe_fruit_ratio"),
        leaf_density=_float_field(data, "leaf_density"),
        disease_spot_ratio=_float_field(data, "disease_spot_ratio"),
    )


def work_history_event_from_json(data: JsonObject) -> WorkHistoryEvent:
    return WorkHistoryEvent(
        timestamp=_required_str(data, "timestamp"),
        action_type=_required_str(data, "action_type"),
        source=_required_str(data, "source"),
        notes=_optional_str(data, "notes") or "",
    )


def action_candidate_from_json(data: JsonObject) -> ActionCandidate:
    return ActionCandidate(
        action_type=_action_type_field(data, "action_type"),
        target_window=_required_str(data, "target_window"),
        rationale=_required_str(data, "rationale"),
        constraints=tuple(_str_list_field(data, "constraints")),
    )


def prediction_result_from_json(data: JsonObject) -> PredictionResult:
    return PredictionResult(
        target=_required_str(data, "target"),
        horizon_hours=_int_field(data, "horizon_hours") or 0,
        predicted_value=_float_field(data, "predicted_value"),
        predicted_delta=_float_field(data, "predicted_delta"),
        confidence=_float_field(data, "confidence") or 0.0,
        model_used=_required_str(data, "model_used"),
        fallback_used=_bool_field(data, "fallback_used") or False,
        metrics=_metric_items(_object_field(data, "metrics", required=False)),
    )


def evidence_reference_from_json(data: JsonObject) -> EvidenceReference:
    return EvidenceReference(
        source_type=_required_str(data, "source_type"),
        title=_required_str(data, "title"),
        reference_id=_required_str(data, "reference_id"),
        url=_optional_str(data, "url"),
        note=_optional_str(data, "note") or "",
        confidence=_float_field(data, "confidence") or 1.0,
    )


def recommendation_result_from_json(data: JsonObject) -> RecommendationResult:
    candidate_data = _object_field(data, "action_candidate", required=False)
    prediction_data = _object_field(data, "prediction", required=False)
    return RecommendationResult(
        action_type=_action_type_field(data, "action_type"),
        priority=_priority_field(data, "priority"),
        confidence=_float_field(data, "confidence") or 0.0,
        reason=_required_str(data, "reason"),
        expected_effect=_required_str(data, "expected_effect"),
        risks=tuple(_str_list_field(data, "risks")),
        evidence_references=tuple(
            evidence_reference_from_json(item)
            for item in _object_list_field(data, "evidence_references")
        ),
        safety_flags=tuple(_str_list_field(data, "safety_flags")),
        model_used=_required_str(data, "model_used"),
        fallback_used=_bool_field(data, "fallback_used") or False,
        action_candidate=action_candidate_from_json(candidate_data) if candidate_data else None,
        prediction=prediction_result_from_json(prediction_data) if prediction_data else None,
    )


def _json_object(value: JsonValue, field_name: str) -> JsonObject:
    match value:
        case dict():
            return value
        case _:
            raise DecisionContractError(field_name, "must be an object")


def _object_field(data: JsonObject, field_name: str, required: bool = True) -> JsonObject:
    value = data.get(field_name)
    if value is None and not required:
        return {}
    return _json_object(value, field_name)


def _object_list_field(data: JsonObject, field_name: str) -> list[JsonObject]:
    value = data.get(field_name, [])
    match value:
        case list():
            return [_json_object(item, field_name) for item in value]
        case _:
            raise DecisionContractError(field_name, "must be a list")


def _required_str(data: JsonObject, field_name: str) -> str:
    value = data.get(field_name)
    match value:
        case str():
            return value
        case None:
            raise DecisionContractError(field_name, "is required")
        case _:
            raise DecisionContractError(field_name, "must be a string")


def _optional_str(data: JsonObject, field_name: str) -> str | None:
    value = data.get(field_name)
    match value:
        case None:
            return None
        case str():
            return value
        case _:
            raise DecisionContractError(field_name, "must be a string")


def _float_field(data: JsonObject, field_name: str) -> float | None:
    value = data.get(field_name)
    match value:
        case None:
            return None
        case bool():
            raise DecisionContractError(field_name, "must be a number")
        case int() | float():
            return float(value)
        case _:
            raise DecisionContractError(field_name, "must be a number")


def _int_field(data: JsonObject, field_name: str) -> int | None:
    value = data.get(field_name)
    match value:
        case None:
            return None
        case bool():
            raise DecisionContractError(field_name, "must be an integer")
        case int():
            return value
        case _:
            raise DecisionContractError(field_name, "must be an integer")


def _bool_field(data: JsonObject, field_name: str) -> bool | None:
    value = data.get(field_name)
    match value:
        case None:
            return None
        case bool():
            return value
        case _:
            raise DecisionContractError(field_name, "must be a boolean")


def _str_list_field(data: JsonObject, field_name: str) -> list[str]:
    value = data.get(field_name, [])
    match value:
        case list():
            result: list[str] = []
            for item in value:
                match item:
                    case str():
                        result.append(item)
                    case _:
                        raise DecisionContractError(field_name, "must contain only strings")
            return result
        case _:
            raise DecisionContractError(field_name, "must be a list")


def _action_type_field(data: JsonObject, field_name: str) -> ActionType:
    value = _required_str(data, field_name)
    if value not in ACTION_TYPES:
        raise DecisionContractError(field_name, f"unsupported action type: {value}")
    return value


def _priority_field(data: JsonObject, field_name: str) -> Priority:
    value = _required_str(data, field_name)
    if value not in PRIORITIES:
        raise DecisionContractError(field_name, f"unsupported priority: {value}")
    return value


def _metric_items(data: JsonObject) -> tuple[tuple[str, float], ...]:
    metrics: list[tuple[str, float]] = []
    for key, value in data.items():
        match value:
            case bool():
                raise DecisionContractError(f"metrics.{key}", "must be a number")
            case int() | float():
                metrics.append((key, float(value)))
            case _:
                raise DecisionContractError(f"metrics.{key}", "must be a number")
    return tuple(metrics)
