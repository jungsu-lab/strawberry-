from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .greenhouse_models import GreenhouseEnvironment, GreenhouseState


DEFAULT_CANDIDATES: Final = (
    "irrigation",
    "no_irrigation",
    "lower_ec_nutrient_adjustment",
    "raise_ec_check_supplied_ec",
    "ventilation",
    "no_ventilation",
    "shading",
    "no_shading",
    "heat_preservation_heating_review",
    "no_heat_preservation",
)
NOT_TRAINING_LABEL_NOTICE: Final = (
    "Scenario outputs are heuristic decision-support comparisons, not ground-truth labels "
    "and not fake supervised farmwork labels."
)


@dataclass(frozen=True, slots=True)
class ShortHorizonScenarioResult:
    action_type: str
    horizon_hours: int
    moisture_delta: float
    ec_delta: float
    salinity_stress_delta: float
    humidity_delta: float
    vpd_delta: float
    temperature_delta: float
    disease_environment_risk_delta: float
    energy_cost_delta: float
    confidence: float
    expected_benefits: tuple[str, ...]
    risks: tuple[str, ...]
    warnings: tuple[str, ...]
    evidence_rule_ids: tuple[str, ...]
    evidence_tags: tuple[str, ...]
    notes: tuple[str, ...]
    model_status: str = "heuristic_prototype"
    is_training_label: bool = False


@dataclass(frozen=True, slots=True)
class ShortHorizonScenarioComparison:
    horizon_hours: int
    scenarios: tuple[ShortHorizonScenarioResult, ...]
    not_training_label_notice: str = NOT_TRAINING_LABEL_NOTICE


def compare_action_candidates(
    state: GreenhouseState,
    environment: GreenhouseEnvironment,
    *,
    horizon_hours: int = 3,
    candidates: tuple[str, ...] = DEFAULT_CANDIDATES,
) -> ShortHorizonScenarioComparison:
    horizon = max(1, min(horizon_hours, 3))
    return ShortHorizonScenarioComparison(
        horizon_hours=horizon,
        scenarios=tuple(_simulate_candidate(candidate, state, environment, horizon) for candidate in candidates),
    )


def _simulate_candidate(
    action_type: str,
    state: GreenhouseState,
    environment: GreenhouseEnvironment,
    horizon_hours: int,
) -> ShortHorizonScenarioResult:
    if action_type not in DEFAULT_CANDIDATES:
        raise ValueError(f"unsupported candidate action: {action_type}")
    match action_type:
        case "irrigation":
            return _irrigation(state, environment, horizon_hours)
        case "no_irrigation":
            return _no_irrigation(environment, horizon_hours)
        case "lower_ec_nutrient_adjustment":
            return _lower_ec(state, horizon_hours)
        case "raise_ec_check_supplied_ec":
            return _raise_ec_check(state, horizon_hours)
        case "ventilation":
            return _ventilation(environment, horizon_hours)
        case "no_ventilation":
            return _no_ventilation(environment, horizon_hours)
        case "shading":
            return _shading(environment, horizon_hours)
        case "no_shading":
            return _no_shading(environment, horizon_hours)
        case "heat_preservation_heating_review":
            return _heat_preservation(environment, horizon_hours)
        case "no_heat_preservation":
            return _no_heat_preservation(environment, horizon_hours)
        case _:
            raise ValueError(f"unsupported candidate action: {action_type}")


def _irrigation(
    state: GreenhouseState,
    environment: GreenhouseEnvironment,
    horizon: int,
) -> ShortHorizonScenarioResult:
    drydown = _drydown(environment, horizon)
    moisture_delta = max(4.0, 12.0 - drydown)
    ec_delta = -0.08 * horizon
    disease_delta = 0.04 if state.substrate_moisture_pct + moisture_delta >= 80.0 else 0.0
    return _result(
        "irrigation",
        horizon,
        moisture_delta=moisture_delta,
        ec_delta=ec_delta,
        salinity_stress_delta=-8.0,
        disease_environment_risk_delta=disease_delta,
        expected_benefits=("root-zone moisture may improve", "EC/salinity stress may dilute if drainage is adequate"),
        risks=("over-wet substrate can raise disease-environment risk",),
        warnings=("confirm recent irrigation and drainage before action",),
        evidence_rule_ids=("irrigation.solar_moisture_vpd.001",),
        evidence_tags=("irrigation_transpiration", "irrigation_ec_drainage"),
    )


def _no_irrigation(environment: GreenhouseEnvironment, horizon: int) -> ShortHorizonScenarioResult:
    return _result(
        "no_irrigation",
        horizon,
        moisture_delta=-_drydown(environment, horizon),
        expected_benefits=("avoids over-wet substrate risk",),
        risks=("water stress may persist under high VPD or radiation",),
        warnings=("monitor substrate moisture trend",),
        evidence_rule_ids=("irrigation.solar_moisture_vpd.001",),
    )


def _lower_ec(state: GreenhouseState, horizon: int) -> ShortHorizonScenarioResult:
    del state
    return _result(
        "lower_ec_nutrient_adjustment",
        horizon,
        ec_delta=-0.12 * horizon,
        salinity_stress_delta=-18.0,
        expected_benefits=("salinity stress may decrease after nutrient adjustment review",),
        risks=("over-dilution can reduce nutrient availability",),
        warnings=("verify feed EC, drain EC, and drainage ratio first",),
        evidence_rule_ids=("nutrient.ec_check.001",),
        evidence_tags=("nutrient_seolhyang_ec",),
    )


def _raise_ec_check(state: GreenhouseState, horizon: int) -> ShortHorizonScenarioResult:
    del state
    return _result(
        "raise_ec_check_supplied_ec",
        horizon,
        ec_delta=0.06 * horizon,
        salinity_stress_delta=4.0,
        expected_benefits=("supplied EC issue becomes better characterized",),
        risks=("raising EC can increase salinity stress if drain EC is already high",),
        warnings=("treat as EC check, not automatic fertilizer increase",),
        evidence_rule_ids=("nutrient.ec_check.001",),
        evidence_tags=("nutrient_seolhyang_ec",),
    )


def _ventilation(environment: GreenhouseEnvironment, horizon: int) -> ShortHorizonScenarioResult:
    humidity_delta = -min(12.0, 3.0 * horizon)
    vpd_delta = 0.08 * horizon
    temp_delta = -0.4 * horizon if environment.inside_temperature_c > 10.0 else -0.1 * horizon
    return _result(
        "ventilation",
        horizon,
        humidity_delta=humidity_delta,
        vpd_delta=vpd_delta,
        temperature_delta=temp_delta,
        disease_environment_risk_delta=-0.1,
        energy_cost_delta=2.0,
        expected_benefits=("humidity and disease-environment risk proxy may decrease",),
        risks=("temperature may drop if outside air is cold",),
        warnings=("human review required before control changes",),
        evidence_rule_ids=("environment.ventilation_dehumidification.001",),
    )


def _no_ventilation(environment: GreenhouseEnvironment, horizon: int) -> ShortHorizonScenarioResult:
    humid_pressure = 0.03 * horizon if environment.humidity_pct >= 85.0 else 0.0
    return _result(
        "no_ventilation",
        horizon,
        humidity_delta=1.0 * horizon if environment.humidity_pct >= 85.0 else 0.0,
        disease_environment_risk_delta=humid_pressure,
        expected_benefits=("avoids cold-air ventilation side effects",),
        risks=("humidity and wet-canopy pressure may persist",),
        warnings=("do not ignore sustained high humidity",),
        evidence_rule_ids=("environment.ventilation_dehumidification.001",),
    )


def _shading(environment: GreenhouseEnvironment, horizon: int) -> ShortHorizonScenarioResult:
    temp_delta = -0.8 * horizon if environment.solar_radiation_w_m2 >= 500.0 else -0.3 * horizon
    vpd_delta = -0.08 * horizon
    return _result(
        "shading",
        horizon,
        moisture_delta=1.5,
        humidity_delta=1.0,
        vpd_delta=vpd_delta,
        temperature_delta=temp_delta,
        expected_benefits=("heat and radiation stress may decrease", "water demand may decrease"),
        risks=("excess shading can reduce photosynthesis",),
        warnings=("compare with radiation forecast and growth stage",),
        evidence_rule_ids=("environment.shading_high_temperature.001",),
    )


def _no_shading(environment: GreenhouseEnvironment, horizon: int) -> ShortHorizonScenarioResult:
    heat_delta = 0.4 * horizon if environment.solar_radiation_w_m2 >= 650.0 else 0.0
    return _result(
        "no_shading",
        horizon,
        moisture_delta=-_drydown(environment, horizon) * 0.5,
        vpd_delta=0.05 * horizon if environment.vpd_kpa >= 1.2 else 0.0,
        temperature_delta=heat_delta,
        expected_benefits=("keeps full light for photosynthesis",),
        risks=("heat/radiation stress may persist",),
        warnings=("monitor VPD and fruit temperature proxy",),
        evidence_rule_ids=("environment.shading_high_temperature.001",),
    )


def _heat_preservation(environment: GreenhouseEnvironment, horizon: int) -> ShortHorizonScenarioResult:
    temp_delta = 1.2 * horizon if environment.inside_temperature_c <= 15.0 else 0.5 * horizon
    return _result(
        "heat_preservation_heating_review",
        horizon,
        humidity_delta=1.0,
        temperature_delta=temp_delta,
        disease_environment_risk_delta=0.02,
        energy_cost_delta=8.0 * horizon,
        expected_benefits=("low-temperature risk may decrease",),
        risks=("energy cost increases", "humidity may rise when ventilation is reduced"),
        warnings=("review energy and humidity tradeoff before heating",),
        evidence_rule_ids=("environment.heating_low_temperature.001",),
    )


def _no_heat_preservation(environment: GreenhouseEnvironment, horizon: int) -> ShortHorizonScenarioResult:
    temp_delta = -0.5 * horizon if environment.inside_temperature_c <= 15.0 else 0.0
    return _result(
        "no_heat_preservation",
        horizon,
        temperature_delta=temp_delta,
        expected_benefits=("avoids heating energy cost",),
        risks=("low-temperature stress may persist",),
        warnings=("monitor nighttime temperature forecast",),
        evidence_rule_ids=("environment.heating_low_temperature.001",),
    )


def _result(
    action_type: str,
    horizon: int,
    moisture_delta: float = 0.0,
    ec_delta: float = 0.0,
    salinity_stress_delta: float = 0.0,
    humidity_delta: float = 0.0,
    vpd_delta: float = 0.0,
    temperature_delta: float = 0.0,
    disease_environment_risk_delta: float = 0.0,
    energy_cost_delta: float = 0.0,
    expected_benefits: tuple[str, ...] = (),
    risks: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
    evidence_rule_ids: tuple[str, ...] = (),
    evidence_tags: tuple[str, ...] = (),
) -> ShortHorizonScenarioResult:
    return ShortHorizonScenarioResult(
        action_type=action_type,
        horizon_hours=horizon,
        moisture_delta=round(moisture_delta, 3),
        ec_delta=round(ec_delta, 3),
        salinity_stress_delta=round(salinity_stress_delta, 3),
        humidity_delta=round(humidity_delta, 3),
        vpd_delta=round(vpd_delta, 3),
        temperature_delta=round(temperature_delta, 3),
        disease_environment_risk_delta=round(disease_environment_risk_delta, 3),
        energy_cost_delta=round(energy_cost_delta, 3),
        confidence=0.48 if warnings else 0.56,
        expected_benefits=expected_benefits,
        risks=risks,
        warnings=warnings,
        evidence_rule_ids=evidence_rule_ids,
        evidence_tags=evidence_tags,
        notes=("heuristic prototype comparison only", NOT_TRAINING_LABEL_NOTICE),
    )


def _drydown(environment: GreenhouseEnvironment, horizon: int) -> float:
    loss = 1.5 * horizon
    if environment.solar_radiation_w_m2 >= 650.0 or environment.vpd_kpa >= 1.2:
        loss += 1.2 * horizon
    return loss
