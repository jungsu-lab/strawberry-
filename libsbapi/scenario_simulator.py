from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Callable, Mapping
from typing import Final, Literal, TypeAlias, override

from libsbapi.decision_contract import EvidenceReference, GreenhouseSnapshot, PredictionResult
from libsbapi.evidence_rules import EvidenceRule, evidence_rules_by_action_type
from libsbapi.prediction_confidence import gate_prediction_result
from libsbapi.prediction_targets import prediction_relates_to_action


ScenarioAction = Literal[
    "irrigation",
    "no_irrigation",
    "lower_ec_nutrient_adjustment",
    "raise_ec_check_supplied_ec",
    "ventilation_dehumidification",
    "ventilation",
    "no_ventilation",
    "shading_high_temperature",
    "shading",
    "no_shading",
    "heating_low_temperature",
    "heat_preservation_heating_review",
    "no_heat_preservation",
    "nutrient_ec_check",
    "no_action",
]
SUPPORTED_ACTIONS: Final = frozenset(
    {
        "irrigation",
        "no_irrigation",
        "lower_ec_nutrient_adjustment",
        "raise_ec_check_supplied_ec",
        "ventilation_dehumidification",
        "ventilation",
        "no_ventilation",
        "shading_high_temperature",
        "shading",
        "no_shading",
        "heating_low_temperature",
        "heat_preservation_heating_review",
        "no_heat_preservation",
        "nutrient_ec_check",
        "no_action",
    }
)
ScenarioSimulator: TypeAlias = Callable[["ScenarioContext"], "ScenarioSimulationResult"]
NOT_VALIDATED_WARNING: Final = (
    "This is a what-if scenario estimate, not a validated causal simulation or control command."
)


@dataclass(frozen=True, slots=True)
class ScenarioSimulatorError(ValueError):
    field_name: str
    detail: str

    @override
    def __str__(self) -> str:
        return f"{self.field_name}: {self.detail}"


@dataclass(frozen=True, slots=True)
class ScenarioCandidate:
    action_type: ScenarioAction

    def __post_init__(self) -> None:
        if self.action_type not in SUPPORTED_ACTIONS:
            raise ScenarioSimulatorError("action_type", f"unsupported action: {self.action_type}")


@dataclass(frozen=True, slots=True)
class ScenarioSimulationRequest:
    snapshot: GreenhouseSnapshot
    candidate_actions: tuple[ScenarioCandidate, ...]
    evidence_rules: tuple[EvidenceRule, ...]
    predictions: tuple[PredictionResult, ...] = ()

    def __post_init__(self) -> None:
        if not self.candidate_actions:
            raise ScenarioSimulatorError("candidate_actions", "must not be empty")


@dataclass(frozen=True, slots=True)
class ScenarioSimulationResult:
    action_type: str
    expected_state_direction: tuple[str, ...]
    potential_benefits: tuple[str, ...]
    potential_risks: tuple[str, ...]
    confidence: float
    evidence_references: tuple[EvidenceReference, ...]
    assumptions: tuple[str, ...]
    not_validated_warning: str = NOT_VALIDATED_WARNING


@dataclass(frozen=True, slots=True)
class ScenarioSimulationReport:
    summary: str
    scenarios: tuple[ScenarioSimulationResult, ...]
    not_validated_warning: str = NOT_VALIDATED_WARNING


@dataclass(frozen=True, slots=True)
class ScenarioContext:
    snapshot: GreenhouseSnapshot
    rules_by_action: Mapping[str, tuple[EvidenceRule, ...]]
    predictions: tuple[PredictionResult, ...]


def simulate_scenarios(request: ScenarioSimulationRequest) -> ScenarioSimulationReport:
    context = ScenarioContext(
        snapshot=request.snapshot,
        rules_by_action=evidence_rules_by_action_type(request.evidence_rules),
        predictions=request.predictions,
    )
    scenarios = tuple(_simulate_candidate(candidate, context) for candidate in request.candidate_actions)
    return ScenarioSimulationReport(
        summary="v0 what-if scenario estimate for decision support; compare directions, not precise effects",
        scenarios=scenarios,
    )


def _simulate_candidate(
    candidate: ScenarioCandidate,
    context: ScenarioContext,
) -> ScenarioSimulationResult:
    result = SCENARIO_SIMULATORS[candidate.action_type](context)
    if result.action_type != candidate.action_type:
        return replace(result, action_type=candidate.action_type)
    return result


def _irrigation(context: ScenarioContext) -> ScenarioSimulationResult:
    directions = ["moisture likely increases"]
    risks = ["humidity risk may increase", "over-wet substrate risk if recent irrigation is ignored"]
    if context.snapshot.root_zone_ec is not None and context.snapshot.root_zone_ec >= 2.2:
        directions.append("EC issue may dilute only if drainage is adequate")
    return _result(
        "irrigation",
        context,
        tuple(directions),
        ("water-stress risk may decrease during high VPD or radiation",),
        tuple(risks),
        0.56,
    )


def _ventilation(context: ScenarioContext) -> ScenarioSimulationResult:
    return _result(
        "ventilation_dehumidification",
        context,
        ("humidity may decrease", "disease environmental risk may decrease"),
        ("wet-canopy pressure may decrease",),
        ("temperature may drop if outside air is cold", "substrate drying may accelerate"),
        0.58,
    )


def _shading(context: ScenarioContext) -> ScenarioSimulationResult:
    return _result(
        "shading_high_temperature",
        context,
        ("heat stress may decrease", "water demand may decrease"),
        ("fruit and canopy heat load may decrease",),
        ("photosynthesis may decrease if shading is excessive",),
        0.5,
    )


def _heating(context: ScenarioContext) -> ScenarioSimulationResult:
    return _result(
        "heating_low_temperature",
        context,
        ("temperature likely increases", "low-temperature stress may decrease"),
        ("flowering, fruiting, or ripening stability may improve",),
        ("energy use may increase", "humidity may rise if ventilation is reduced"),
        0.52,
    )


def _ec_check(context: ScenarioContext) -> ScenarioSimulationResult:
    return _result(
        "nutrient_ec_check",
        context,
        ("EC issue becomes better characterized", "EC issue remains unresolved until fertigation is adjusted"),
        ("salinity or dilution risk may be identified before nutrient changes",),
        ("checking alone does not correct EC",),
        0.6,
    )


def _no_action(context: ScenarioContext) -> ScenarioSimulationResult:
    directions = ["current trend likely continues", "EC issue remains unresolved"]
    if context.snapshot.humidity_pct is not None and context.snapshot.humidity_pct >= 85.0:
        directions.append("disease environmental risk may remain elevated")
    return _result(
        "no_action",
        context,
        tuple(directions),
        ("avoids intervention side effects",),
        ("existing stress signals may persist",),
        0.42,
    )


def _result(
    action_type: str,
    context: ScenarioContext,
    directions: tuple[str, ...],
    benefits: tuple[str, ...],
    risks: tuple[str, ...],
    base_confidence: float,
) -> ScenarioSimulationResult:
    assumptions = (
        "directional v0 estimate based on literature/manual rules",
        "local calibration and human review are required",
        *_prediction_assumptions(action_type, context.predictions),
    )
    confidence = min(base_confidence + _prediction_bonus(action_type, context.predictions), 0.72)
    return ScenarioSimulationResult(
        action_type=action_type,
        expected_state_direction=directions,
        potential_benefits=benefits,
        potential_risks=risks,
        confidence=round(confidence, 3),
        evidence_references=_evidence_references(context.rules_by_action.get(action_type, ())),
        assumptions=assumptions,
    )


def _evidence_references(rules: tuple[EvidenceRule, ...]) -> tuple[EvidenceReference, ...]:
    return tuple(
        EvidenceReference(
            source_type=rule.evidence_level,
            title=rule.source_title,
            reference_id=rule.id,
            note=rule.source_note,
            confidence=0.62,
        )
        for rule in rules
    )


def _prediction_assumptions(
    action_type: str,
    predictions: tuple[PredictionResult, ...],
) -> tuple[str, ...]:
    assumptions: list[str] = []
    for prediction in predictions:
        if prediction_relates_to_action(action_type, prediction):
            gate_decision = gate_prediction_result(prediction)
            if gate_decision.use_model:
                assumptions.append(
                    f"model prediction considered after confidence gate: {prediction.target}"
                )
            else:
                assumptions.append(f"model prediction fallback: {gate_decision.reason}")
    return tuple(assumptions)


def _prediction_bonus(action_type: str, predictions: tuple[PredictionResult, ...]) -> float:
    usable_confidences = _usable_prediction_confidences(action_type, predictions)
    if not usable_confidences:
        return 0.0
    return min(max(usable_confidences), 0.12)


def _usable_prediction_confidences(
    action_type: str,
    predictions: tuple[PredictionResult, ...],
) -> tuple[float, ...]:
    confidences: list[float] = []
    for prediction in predictions:
        if prediction_relates_to_action(action_type, prediction):
            gate_decision = gate_prediction_result(prediction)
            if gate_decision.use_model:
                confidences.append(gate_decision.confidence)
    return tuple(confidences)


SCENARIO_SIMULATORS: Final[Mapping[ScenarioAction, ScenarioSimulator]] = {
    "irrigation": _irrigation,
    "no_irrigation": _no_action,
    "lower_ec_nutrient_adjustment": _ec_check,
    "raise_ec_check_supplied_ec": _ec_check,
    "ventilation_dehumidification": _ventilation,
    "ventilation": _ventilation,
    "no_ventilation": _no_action,
    "shading_high_temperature": _shading,
    "shading": _shading,
    "no_shading": _no_action,
    "heating_low_temperature": _heating,
    "heat_preservation_heating_review": _heating,
    "no_heat_preservation": _no_action,
    "nutrient_ec_check": _ec_check,
    "no_action": _no_action,
}
