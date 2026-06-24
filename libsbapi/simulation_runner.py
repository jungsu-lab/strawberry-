from dataclasses import dataclass, replace

from .greenhouse_models import (
    DiseaseControlWork,
    GreenhouseEnvironment,
    GreenhouseState,
    HarvestWork,
    IrrigationWork,
    LeafPruningWork,
    RunnerRemovalWork,
)
from .greenhouse_rule_helpers import clamp, coloring_daily_rate, disease_pressure_is_high
from .greenhouse_simulator import GreenhouseSimulator, WorkAction


@dataclass(frozen=True, slots=True)
class ScheduledWork:
    day: int
    work: WorkAction


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    initial_state: GreenhouseState
    environment: GreenhouseEnvironment
    days: int
    schedule: tuple[ScheduledWork, ...] = ()


@dataclass(frozen=True, slots=True)
class SimulationRecord:
    scenario: str
    day: int
    action: str
    substrate_moisture_pct: float
    drain_ec: float
    disease_risk: float
    ripe_fruit_ratio: float
    fruit_count: int
    leaf_density: float
    ventilation_score: float
    yield_potential: float
    marketable_yield_kg: float
    quality_risk: float
    notes: str
    warnings: str
    evidence_tags: str
    confidence: float


@dataclass(frozen=True, slots=True)
class EvidenceLogEntry:
    scenario: str
    day: int
    action: str
    kind: str
    message: str


@dataclass(frozen=True, slots=True)
class ScenarioComparison:
    timeline: tuple[SimulationRecord, ...]
    end_states: tuple[SimulationRecord, ...]
    evidence_log: tuple[EvidenceLogEntry, ...]


@dataclass(frozen=True, slots=True)
class _RecordInput:
    scenario: str
    day: int
    action: str
    state: GreenhouseState
    notes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence_tags: tuple[str, ...] = ()
    confidence: float = 1.0


def simulate_scenario(scenario: Scenario) -> tuple[SimulationRecord, ...]:
    simulator = GreenhouseSimulator()
    state = scenario.initial_state
    records = [
        _record_from_input(
            _RecordInput(
                scenario=scenario.name,
                day=0,
                action="initial",
                state=state,
            ),
        ),
    ]

    for day in range(1, max(0, scenario.days) + 1):
        works = _works_for_day(scenario.schedule, day)
        action_notes: list[str] = []
        action_warnings: list[str] = []
        action_evidence: list[str] = []
        action_confidences: list[float] = []

        for work in works:
            step = simulator.apply(state, scenario.environment, work)
            state = step.state
            action_notes.extend(step.notes)
            action_warnings.extend(step.warnings)
            action_evidence.extend(tag.value for tag in step.evidence_tags)
            action_confidences.append(step.confidence)
            action_notes.extend(f"{name}={value:g}" for name, value in step.metrics)

        ambient = _apply_ambient_drift(state, scenario.environment)
        state = ambient.state
        action_notes.extend(ambient.notes)
        action_warnings.extend(ambient.warnings)

        records.append(
            _record_from_input(
                _RecordInput(
                    scenario=scenario.name,
                    day=day,
                    action=_action_label(works),
                    state=state,
                    notes=tuple(dict.fromkeys(action_notes)),
                    warnings=tuple(dict.fromkeys(action_warnings)),
                    evidence_tags=tuple(dict.fromkeys(action_evidence)),
                    confidence=_combined_confidence(action_confidences, action_warnings),
                ),
            ),
        )

    return tuple(records)


def compare_scenarios(scenarios: tuple[Scenario, ...]) -> ScenarioComparison:
    timeline: list[SimulationRecord] = []
    end_states: list[SimulationRecord] = []
    evidence_log: list[EvidenceLogEntry] = []

    for scenario in scenarios:
        records = simulate_scenario(scenario)
        timeline.extend(records)
        if records:
            end_states.append(records[-1])
        evidence_log.extend(_evidence_entries(records))

    return ScenarioComparison(
        timeline=tuple(timeline),
        end_states=tuple(end_states),
        evidence_log=tuple(evidence_log),
    )


@dataclass(frozen=True, slots=True)
class _AmbientStep:
    state: GreenhouseState
    notes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _apply_ambient_drift(
    state: GreenhouseState,
    environment: GreenhouseEnvironment,
) -> _AmbientStep:
    notes: list[str] = []
    warnings: list[str] = []
    moisture_loss = 2.0
    disease_risk = state.disease_risk
    ripe_fruit_ratio = state.ripe_fruit_ratio
    quality_risk = state.quality_risk
    coloring_pct = state.coloring_pct

    if environment.solar_radiation_w_m2 >= 650.0 or environment.vpd_kpa >= 1.2:
        moisture_loss += 3.0
        notes.append("ambient high solar/VPD reduced substrate moisture")

    if disease_pressure_is_high(state, environment):
        disease_risk += 0.04
        notes.append("ambient humid/rainy pressure increased disease risk")

    if state.leaf_density >= 0.8 and state.ventilation_score <= 0.35:
        disease_risk += 0.03
        warnings.append("dense canopy and low ventilation kept disease risk elevated")

    ripe_fruit_ratio = clamp(ripe_fruit_ratio + 0.04)

    if coloring_pct is not None:
        coloring_pct = clamp(
            coloring_pct + coloring_daily_rate(state.distribution_type),
            high=100.0,
        )

    if environment.inside_temperature_c >= 28.0 or environment.rain_probability >= 60.0:
        quality_risk += 0.03
        notes.append("ambient heat/rain increased quality risk")

    return _AmbientStep(
        state=replace(
            state,
            substrate_moisture_pct=clamp(state.substrate_moisture_pct - moisture_loss, high=100.0),
            disease_risk=clamp(disease_risk),
            ripe_fruit_ratio=ripe_fruit_ratio,
            quality_risk=clamp(quality_risk),
            coloring_pct=coloring_pct,
        ),
        notes=tuple(notes),
        warnings=tuple(warnings),
    )


def _works_for_day(schedule: tuple[ScheduledWork, ...], day: int) -> tuple[WorkAction, ...]:
    return tuple(item.work for item in schedule if item.day == day)


def _action_label(works: tuple[WorkAction, ...]) -> str:
    if not works:
        return "ambient"
    return ", ".join(_work_label(work) for work in works)


def _work_label(work: WorkAction) -> str:
    match work:
        case IrrigationWork():
            return "irrigation"
        case DiseaseControlWork():
            return "disease_control"
        case HarvestWork():
            return "harvest"
        case LeafPruningWork():
            return "leaf_pruning"
        case RunnerRemovalWork():
            return "runner_removal"


def _record_from_input(record: _RecordInput) -> SimulationRecord:
    return SimulationRecord(
        scenario=record.scenario,
        day=record.day,
        action=record.action,
        substrate_moisture_pct=round(record.state.substrate_moisture_pct, 3),
        drain_ec=round(record.state.drain_ec, 3),
        disease_risk=round(record.state.disease_risk, 3),
        ripe_fruit_ratio=round(record.state.ripe_fruit_ratio, 3),
        fruit_count=record.state.fruit_count,
        leaf_density=round(record.state.leaf_density, 3),
        ventilation_score=round(record.state.ventilation_score, 3),
        yield_potential=round(record.state.yield_potential, 3),
        marketable_yield_kg=round(record.state.marketable_yield_kg, 3),
        quality_risk=round(record.state.quality_risk, 3),
        notes="; ".join(record.notes),
        warnings="; ".join(record.warnings),
        evidence_tags="; ".join(record.evidence_tags),
        confidence=round(record.confidence, 3),
    )


def _combined_confidence(confidences: list[float], warnings: list[str]) -> float:
    base = min(confidences) if confidences else 1.0
    return clamp(base - len(warnings) * 0.04)


def _evidence_entries(records: tuple[SimulationRecord, ...]) -> tuple[EvidenceLogEntry, ...]:
    entries: list[EvidenceLogEntry] = []
    for record in records:
        entries.extend(_split_messages(record, "note", record.notes))
        entries.extend(_split_messages(record, "warning", record.warnings))
        entries.extend(_split_messages(record, "evidence", record.evidence_tags))
    return tuple(entries)


def _split_messages(
    record: SimulationRecord,
    kind: str,
    messages: str,
) -> tuple[EvidenceLogEntry, ...]:
    return tuple(
        EvidenceLogEntry(
            scenario=record.scenario,
            day=record.day,
            action=record.action,
            kind=kind,
            message=message.strip(),
        )
        for message in messages.split(";")
        if message.strip()
    )
