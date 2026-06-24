from dataclasses import replace
from typing import assert_never

from .greenhouse_models import (
    DiseaseControlMethod,
    DiseaseControlWork,
    DistributionType,
    EvidenceTag,
    GreenhouseEnvironment,
    GreenhouseState,
    HarvestWork,
    IrrigationWork,
    LeafPruningWork,
    RunnerRemovalWork,
    SimulationStep,
)
from .greenhouse_rule_helpers import (
    botrytis_bloom_pressure_is_high,
    clamp,
    confidence,
    control_effectiveness,
    defoliation_is_excessive,
    disease_pressure_is_high,
    harvest_coloring_is_risky,
    harvest_coloring_warning,
    harvest_delay_pressure_is_high,
    irrigation_evidence,
    irrigation_notes,
    irrigation_warnings,
    expected_days_to_100_coloring,
    unique_tags,
    unique_warnings,
)


WorkAction = (
    IrrigationWork
    | DiseaseControlWork
    | HarvestWork
    | LeafPruningWork
    | RunnerRemovalWork
)


class GreenhouseSimulator:
    def apply(
        self,
        state: GreenhouseState,
        environment: GreenhouseEnvironment,
        work: WorkAction,
    ) -> SimulationStep:
        match work:
            case IrrigationWork():
                return _apply_irrigation(state, environment, work)
            case DiseaseControlWork():
                return _apply_disease_control(state, environment, work)
            case HarvestWork():
                return _apply_harvest(state, environment, work)
            case LeafPruningWork():
                return _apply_leaf_pruning(state, work)
            case RunnerRemovalWork():
                return _apply_runner_removal(state, work)
            case unreachable:
                assert_never(unreachable)


def _apply_irrigation(
    state: GreenhouseState,
    environment: GreenhouseEnvironment,
    work: IrrigationWork,
) -> SimulationStep:
    volume_l = max(0.0, work.volume_l)
    notes = irrigation_notes(volume_l, state, environment)
    warnings = irrigation_warnings(state)
    evidence_tags = irrigation_evidence(state, environment)
    moisture = state.substrate_moisture_pct + volume_l * 11.0
    drain_ec = state.drain_ec - volume_l * 0.12
    disease_risk = state.disease_risk
    yield_potential = state.yield_potential

    if environment.solar_radiation_w_m2 >= 650 or environment.vpd_kpa >= 1.2:
        moisture -= 8.0

    if moisture >= 80.0:
        disease_risk += 0.12

    if state.substrate_vwc_m3_m3 is not None and state.substrate_vwc_m3_m3 < 0.18:
        yield_potential -= 0.08

    if state.substrate_vwc_m3_m3 is not None and state.substrate_vwc_m3_m3 > 0.30:
        disease_risk += 0.06

    return SimulationStep(
        state=replace(
            state,
            substrate_moisture_pct=clamp(moisture, high=100.0),
            drain_ec=clamp(drain_ec, high=5.0),
            disease_risk=clamp(disease_risk),
            yield_potential=clamp(yield_potential),
        ),
        notes=tuple(notes),
        evidence_tags=tuple(evidence_tags),
        warnings=tuple(warnings),
        confidence=confidence(warnings),
    )


def _apply_disease_control(
    state: GreenhouseState,
    environment: GreenhouseEnvironment,
    work: DiseaseControlWork,
) -> SimulationStep:
    notes = ["disease control reduced disease risk"]
    warnings: list[str] = []
    evidence_tags = [EvidenceTag.DISEASE_ADVISORY_SYSTEM]
    effectiveness = control_effectiveness(work, warnings)
    disease_risk = state.disease_risk * (1.0 - effectiveness * 0.75)

    if disease_pressure_is_high(state, environment):
        disease_risk += 0.18
        notes.append("humid/rainy conditions rebuilt disease pressure")

    if botrytis_bloom_pressure_is_high(state, environment):
        disease_risk += 0.08
        notes.append("flowering and wet canopy kept Botrytis pressure high")
        evidence_tags.append(EvidenceTag.DISEASE_BOTRYTIS_FLOWERING)

    if state.days_since_fungicide is not None and state.days_since_fungicide <= 3:
        warnings.append("recent fungicide history should be checked before another spray")

    return SimulationStep(
        state=replace(state, disease_risk=clamp(disease_risk)),
        notes=tuple(notes),
        evidence_tags=tuple(unique_tags(evidence_tags)),
        warnings=tuple(warnings),
        confidence=confidence(warnings),
    )


def _apply_harvest(
    state: GreenhouseState,
    environment: GreenhouseEnvironment,
    work: HarvestWork,
) -> SimulationStep:
    notes = ["harvest removed ripe fruit and added marketable yield"]
    warnings: list[str] = []
    evidence_tags = [EvidenceTag.HARVEST_SEOLHYANG_COLORING]
    picked_ratio = clamp(work.pick_ratio)
    picked_fruit = round(state.fruit_count * state.ripe_fruit_ratio * picked_ratio)
    fruit_count = max(0, state.fruit_count - picked_fruit)
    marketable_yield_kg = state.marketable_yield_kg + picked_fruit * 0.018 * state.yield_potential
    ripe_fruit_ratio = state.ripe_fruit_ratio * (1.0 - picked_ratio)
    quality_risk = state.quality_risk
    metrics = _harvest_metrics(state)

    if harvest_coloring_is_risky(state):
        quality_risk += 0.12
        warnings.append(harvest_coloring_warning(state.distribution_type))

    if work.delayed_days >= 1 and harvest_delay_pressure_is_high(environment):
        quality_risk += 0.1 * work.delayed_days
        marketable_yield_kg *= 0.96
        notes.append("delayed harvest under heat/rain increased quality risk")

    if environment.month is not None and environment.month >= 4:
        quality_risk += 0.06
        warnings.append("late-season heat can reduce firmness and sweetness")

    return SimulationStep(
        state=replace(
            state,
            ripe_fruit_ratio=clamp(ripe_fruit_ratio),
            fruit_count=fruit_count,
            marketable_yield_kg=round(marketable_yield_kg, 3),
            quality_risk=clamp(quality_risk),
        ),
        notes=tuple(notes),
        evidence_tags=tuple(evidence_tags),
        warnings=tuple(warnings),
        metrics=metrics,
        confidence=confidence(warnings),
    )


def _apply_leaf_pruning(state: GreenhouseState, work: LeafPruningWork) -> SimulationStep:
    notes = ["leaf pruning reduced canopy density and improved ventilation"]
    warnings: list[str] = []
    evidence_tags = [EvidenceTag.CANOPY_DEFOLIATION_LIMIT]
    removal_ratio = clamp(work.removal_ratio)
    leaf_density = state.leaf_density * (1.0 - removal_ratio)
    ventilation_score = state.ventilation_score + removal_ratio * 0.55
    disease_risk = state.disease_risk - removal_ratio * 0.45
    yield_potential = state.yield_potential

    if state.old_or_diseased_leaf_level >= 0.6:
        disease_risk -= 0.05
        notes.append("diseased or old leaves made partial defoliation more useful")

    if defoliation_is_excessive(state, removal_ratio, leaf_density):
        yield_potential -= 0.12
        notes.append("excessive leaf removal reduced photosynthetic area")
        warnings.append("leaf count is already low; avoid normal-leaf defoliation")

    if state.fruit_count >= 90 and removal_ratio >= 0.2:
        yield_potential -= 0.04
        warnings.append("high fruit load makes aggressive defoliation risky")

    return SimulationStep(
        state=replace(
            state,
            leaf_density=clamp(leaf_density),
            ventilation_score=clamp(ventilation_score),
            disease_risk=clamp(disease_risk),
            yield_potential=clamp(yield_potential),
        ),
        notes=tuple(notes),
        evidence_tags=tuple(evidence_tags),
        warnings=tuple(unique_warnings(warnings)),
        confidence=confidence(warnings),
    )


def _apply_runner_removal(state: GreenhouseState, work: RunnerRemovalWork) -> SimulationStep:
    removed = min(max(0, work.remove_count), state.runner_count)
    runner_count = state.runner_count - removed
    yield_bonus = 0.04
    if state.fruit_count >= 70 or state.flower_count >= 20:
        yield_bonus = 0.08

    return SimulationStep(
        state=replace(
            state,
            runner_count=runner_count,
            yield_potential=clamp(state.yield_potential + yield_bonus),
        ),
        notes=("runner removal reduced sink competition",),
        evidence_tags=(EvidenceTag.CANOPY_RUNNER_REMOVAL,),
    )


def _harvest_metrics(state: GreenhouseState) -> tuple[tuple[str, float], ...]:
    expected_days = expected_days_to_100_coloring(state)
    if expected_days is None:
        return ()
    return (("expected_days_to_100_coloring", expected_days),)
