from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from libsbapi.decision_contract import EvidenceReference
from libsbapi.decision_contract_io import (
    JsonObject,
    JsonValue,
    greenhouse_snapshot_from_json,
    prediction_result_from_json,
)
from libsbapi.evidence_rules import EvidenceRule
from libsbapi.scenario_simulator import (
    ScenarioAction,
    ScenarioCandidate,
    ScenarioSimulationReport,
    ScenarioSimulationRequest,
    ScenarioSimulationResult,
    ScenarioSimulatorError,
)


SCENARIO_ACTIONS_BY_VALUE: Final[dict[str, ScenarioAction]] = {
    "irrigation": "irrigation",
    "ventilation_dehumidification": "ventilation_dehumidification",
    "shading_high_temperature": "shading_high_temperature",
    "heating_low_temperature": "heating_low_temperature",
    "nutrient_ec_check": "nutrient_ec_check",
    "no_action": "no_action",
}


def load_scenario_simulation_request(
    path: Path,
    evidence_rules: tuple[EvidenceRule, ...],
) -> ScenarioSimulationRequest:
    with path.open(encoding="utf-8") as file:
        payload: JsonValue = json.load(file)
    return scenario_simulation_request_from_json(_json_object(payload, "root"), evidence_rules)


def write_scenario_simulation_report(path: Path, report: ScenarioSimulationReport) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(scenario_report_to_json(report), file, ensure_ascii=False, indent=2)
        _ = file.write("\n")


def scenario_simulation_request_from_json(
    data: JsonObject,
    evidence_rules: tuple[EvidenceRule, ...],
) -> ScenarioSimulationRequest:
    return ScenarioSimulationRequest(
        snapshot=greenhouse_snapshot_from_json(_object_field(data, "snapshot")),
        candidate_actions=tuple(
            ScenarioCandidate(_scenario_action(action))
            for action in _str_list_field(data, "candidate_actions")
        ),
        evidence_rules=evidence_rules,
        predictions=tuple(
            prediction_result_from_json(item)
            for item in _object_list_field(data, "predictions")
        ),
    )


def scenario_report_to_json(report: ScenarioSimulationReport) -> JsonObject:
    return {
        "summary": report.summary,
        "not_validated_warning": report.not_validated_warning,
        "scenarios": [scenario_result_to_json(item) for item in report.scenarios],
    }


def scenario_result_to_json(result: ScenarioSimulationResult) -> JsonObject:
    return {
        "action_type": result.action_type,
        "expected_state_direction": list(result.expected_state_direction),
        "potential_benefits": list(result.potential_benefits),
        "potential_risks": list(result.potential_risks),
        "confidence": result.confidence,
        "evidence_references": [
            evidence_reference_to_json(item) for item in result.evidence_references
        ],
        "assumptions": list(result.assumptions),
        "not_validated_warning": result.not_validated_warning,
    }


def evidence_reference_to_json(reference: EvidenceReference) -> JsonObject:
    return {
        "source_type": reference.source_type,
        "title": reference.title,
        "reference_id": reference.reference_id,
        "url": reference.url,
        "note": reference.note,
        "confidence": reference.confidence,
    }


def _json_object(value: JsonValue, field_name: str) -> JsonObject:
    if isinstance(value, dict):
        return value
    raise ScenarioSimulatorError(field_name, "must be an object")


def _object_field(data: JsonObject, field_name: str) -> JsonObject:
    value = data.get(field_name)
    return _json_object(value, field_name)


def _object_list_field(data: JsonObject, field_name: str) -> list[JsonObject]:
    value = data.get(field_name, [])
    if isinstance(value, list):
        return [_json_object(item, field_name) for item in value]
    raise ScenarioSimulatorError(field_name, "must be a list")


def _str_list_field(data: JsonObject, field_name: str) -> list[str]:
    value = data.get(field_name, [])
    if isinstance(value, list):
        return [_str_item(item, field_name) for item in value]
    raise ScenarioSimulatorError(field_name, "must be a list")


def _str_item(value: JsonValue, field_name: str) -> str:
    if isinstance(value, str):
        return value
    raise ScenarioSimulatorError(field_name, "must contain only strings")


def _scenario_action(value: str) -> ScenarioAction:
    action = SCENARIO_ACTIONS_BY_VALUE.get(value)
    if action is not None:
        return action
    raise ScenarioSimulatorError("candidate_actions", f"unsupported action: {value}")
