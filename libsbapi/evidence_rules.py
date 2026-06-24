from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import TypeAlias


JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

DEFAULT_EVIDENCE_RULES_PATH = Path(__file__).resolve().parents[1] / "config" / "evidence_rules.json"


@dataclass(frozen=True, slots=True)
class EvidenceRuleError(ValueError):
    field_name: str
    detail: str

    def __str__(self) -> str:
        return f"{self.field_name}: {self.detail}"


@dataclass(frozen=True, slots=True)
class EvidenceRule:
    id: str
    action_type: str
    condition_variables: tuple[str, ...]
    condition_description: str
    threshold_or_range: str
    expected_effect: str
    risk_or_caution: str
    evidence_level: str
    source_title: str
    source_note: str
    needs_local_calibration: bool

    def __post_init__(self) -> None:
        _required("id", self.id)
        _required("action_type", self.action_type)
        if not self.condition_variables:
            raise EvidenceRuleError("condition_variables", "must not be empty")
        for variable in self.condition_variables:
            _required("condition_variables", variable)
        _required("condition_description", self.condition_description)
        _required("threshold_or_range", self.threshold_or_range)
        _required("expected_effect", self.expected_effect)
        _required("risk_or_caution", self.risk_or_caution)
        _required("evidence_level", self.evidence_level)
        _required("source_title", self.source_title)
        _required("source_note", self.source_note)


def load_evidence_rules(path: Path = DEFAULT_EVIDENCE_RULES_PATH) -> tuple[EvidenceRule, ...]:
    with path.open(encoding="utf-8") as file:
        payload: JsonValue = json.load(file)
    root = _object(payload, "root")
    return tuple(evidence_rule_from_json(item) for item in _object_list(root, "evidence_rules"))


def evidence_rules_by_action_type(
    rules: tuple[EvidenceRule, ...],
) -> dict[str, tuple[EvidenceRule, ...]]:
    grouped: dict[str, list[EvidenceRule]] = {}
    for rule in rules:
        grouped.setdefault(rule.action_type, []).append(rule)
    return {action_type: tuple(items) for action_type, items in grouped.items()}


def evidence_rule_from_json(data: JsonObject) -> EvidenceRule:
    return EvidenceRule(
        id=_required_str(data, "id"),
        action_type=_required_str(data, "action_type"),
        condition_variables=tuple(_str_list(data, "condition_variables")),
        condition_description=_required_str(data, "condition_description"),
        threshold_or_range=_required_str(data, "threshold_or_range"),
        expected_effect=_required_str(data, "expected_effect"),
        risk_or_caution=_required_str(data, "risk_or_caution"),
        evidence_level=_required_str(data, "evidence_level"),
        source_title=_required_str(data, "source_title"),
        source_note=_required_str(data, "source_note"),
        needs_local_calibration=_required_bool(data, "needs_local_calibration"),
    )


def _required(field_name: str, value: str) -> None:
    if value.strip() == "":
        raise EvidenceRuleError(field_name, "is required")


def _object(value: JsonValue, field_name: str) -> JsonObject:
    match value:
        case dict():
            return value
        case _:
            raise EvidenceRuleError(field_name, "must be an object")


def _object_list(data: JsonObject, field_name: str) -> list[JsonObject]:
    value = data.get(field_name)
    match value:
        case list():
            return [_object(item, field_name) for item in value]
        case None:
            raise EvidenceRuleError(field_name, "is required")
        case _:
            raise EvidenceRuleError(field_name, "must be a list")


def _required_str(data: JsonObject, field_name: str) -> str:
    value = data.get(field_name)
    match value:
        case str():
            return value
        case None:
            raise EvidenceRuleError(field_name, "is required")
        case _:
            raise EvidenceRuleError(field_name, "must be a string")


def _required_bool(data: JsonObject, field_name: str) -> bool:
    value = data.get(field_name)
    match value:
        case bool():
            return value
        case None:
            raise EvidenceRuleError(field_name, "is required")
        case _:
            raise EvidenceRuleError(field_name, "must be a boolean")


def _str_list(data: JsonObject, field_name: str) -> list[str]:
    value = data.get(field_name)
    match value:
        case list():
            result: list[str] = []
            for item in value:
                match item:
                    case str():
                        result.append(item)
                    case _:
                        raise EvidenceRuleError(field_name, "must contain only strings")
            return result
        case None:
            raise EvidenceRuleError(field_name, "is required")
        case _:
            raise EvidenceRuleError(field_name, "must be a list")
