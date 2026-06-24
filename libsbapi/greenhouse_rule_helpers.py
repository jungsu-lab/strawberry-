from math import ceil
from typing import assert_never

from .greenhouse_models import (
    DiseaseControlMethod,
    DiseaseControlWork,
    DistributionType,
    EvidenceTag,
    GreenhouseEnvironment,
    GreenhouseState,
)


def irrigation_notes(
    volume_l: float,
    state: GreenhouseState,
    environment: GreenhouseEnvironment,
) -> list[str]:
    notes = (
        ["irrigation increased substrate moisture"]
        if volume_l > 0.0
        else ["irrigation skipped because volume was non-positive"]
    )
    if environment.solar_radiation_w_m2 >= 650 or environment.vpd_kpa >= 1.2:
        notes.append("high solar/VPD accelerated moisture loss")
    if state.substrate_moisture_pct < 60.0:
        notes.append("substrate moisture was below the Seolhyang force-irrigation candidate")
    if state.substrate_moisture_pct + volume_l * 11.0 >= 80.0:
        notes.append("over-wet substrate increased disease risk")
    return notes


def irrigation_warnings(state: GreenhouseState) -> list[str]:
    warnings = ec_warnings(state)
    if state.drainage_ratio_pct is not None and state.drainage_ratio_pct < 40.0:
        warnings.append("drainage ratio is below the Seolhyang 40-50% target")
    if state.drainage_ratio_pct is not None and state.drainage_ratio_pct > 55.0:
        warnings.append("drainage ratio is above the Seolhyang 40-50% target")
    if state.substrate_vwc_m3_m3 is not None and state.substrate_vwc_m3_m3 < 0.18:
        warnings.append("VWC is below the Seolhyang deficit-irrigation reference")
    if state.substrate_vwc_m3_m3 is not None and state.substrate_vwc_m3_m3 > 0.30:
        warnings.append("VWC is above the full-irrigation reference and may favor vegetative growth")
    return warnings


def irrigation_evidence(
    state: GreenhouseState,
    environment: GreenhouseEnvironment,
) -> list[EvidenceTag]:
    evidence_tags = [EvidenceTag.IRRIGATION_TRANSPIRATION]
    if solar_moisture_triggered(state, environment):
        evidence_tags.append(EvidenceTag.IRRIGATION_SOLAR_MOISTURE)
    if state.feed_ec is not None or state.drainage_ratio_pct is not None:
        evidence_tags.append(EvidenceTag.IRRIGATION_EC_DRAINAGE)
    if state.feed_ec is not None:
        evidence_tags.append(EvidenceTag.NUTRIENT_SEOLHYANG_EC)
    if state.substrate_vwc_m3_m3 is not None:
        evidence_tags.append(EvidenceTag.IRRIGATION_VWC_SENSOR)
    return unique_tags(evidence_tags)


def ec_warnings(state: GreenhouseState) -> list[str]:
    warnings: list[str] = []
    if state.feed_ec is not None and state.drain_ec > state.feed_ec * 1.15:
        warnings.append("drain EC stayed high versus feed EC")
    seolhyang_warning = seolhyang_ec_warning(state)
    if seolhyang_warning is not None:
        warnings.append(seolhyang_warning)
    return warnings


def seolhyang_ec_warning(state: GreenhouseState) -> str | None:
    if state.feed_ec is None:
        return None
    if state.feed_ec < 0.8:
        return "Seolhyang feed EC is below the 0.8-1.5 dS/m candidate range"
    if state.feed_ec > 1.5:
        return "Seolhyang feed EC is above the 0.8-1.5 dS/m candidate range"
    return None


def control_effectiveness(work: DiseaseControlWork, warnings: list[str]) -> float:
    match work.method:
        case DiseaseControlMethod.FUNGICIDE:
            return clamp(work.effectiveness)
        case DiseaseControlMethod.OZONATED_WATER:
            warnings.append("ozonated water is low-confidence for Botrytis control")
            warnings.append("frequent canopy wetting can rebuild disease pressure")
            return min(clamp(work.effectiveness), 0.25)
        case DiseaseControlMethod.SCOUTING:
            return 0.0
        case unreachable:
            assert_never(unreachable)


def disease_pressure_is_high(state: GreenhouseState, environment: GreenhouseEnvironment) -> bool:
    return (
        environment.humidity_pct >= 88.0
        or environment.vpd_kpa <= 0.35
        or environment.rain_probability >= 60.0
        or botrytis_bloom_pressure_is_high(state, environment)
    )


def botrytis_bloom_pressure_is_high(
    state: GreenhouseState,
    environment: GreenhouseEnvironment,
) -> bool:
    flowering = state.flowering_stage_pct is not None and state.flowering_stage_pct >= 60.0
    wet = environment.leaf_wetness_hours is not None and environment.leaf_wetness_hours >= 6.0
    humid = environment.humidity_pct >= 85.0
    return flowering and (wet or humid)


def harvest_coloring_is_risky(state: GreenhouseState) -> bool:
    if state.coloring_pct is None:
        return True
    return state.coloring_pct < harvest_coloring_threshold(state.distribution_type)


def harvest_coloring_threshold(distribution_type: DistributionType) -> float:
    match distribution_type:
        case DistributionType.ROOM_TEMP:
            return 80.0
        case DistributionType.COLD_CHAIN | DistributionType.LOW_TEMP:
            return 90.0
        case unreachable:
            assert_never(unreachable)


def harvest_coloring_warning(distribution_type: DistributionType) -> str:
    match distribution_type:
        case DistributionType.ROOM_TEMP:
            return "room-temperature harvest below 80% coloring has marketability risk"
        case DistributionType.COLD_CHAIN:
            return "cold-chain harvest below 90% coloring has marketability risk"
        case DistributionType.LOW_TEMP:
            return "low-temperature harvest below 90% coloring has marketability risk"
        case unreachable:
            assert_never(unreachable)


def expected_days_to_100_coloring(state: GreenhouseState) -> float | None:
    if state.coloring_pct is None:
        return None
    if state.coloring_pct >= 100.0:
        return 0.0
    daily_rate = coloring_daily_rate(state.distribution_type)
    return float(ceil((100.0 - state.coloring_pct) / daily_rate))


def coloring_daily_rate(distribution_type: DistributionType) -> float:
    match distribution_type:
        case DistributionType.ROOM_TEMP:
            return 10.0
        case DistributionType.COLD_CHAIN:
            return 5.0
        case DistributionType.LOW_TEMP:
            return 3.0
        case unreachable:
            assert_never(unreachable)


def harvest_delay_pressure_is_high(environment: GreenhouseEnvironment) -> bool:
    return environment.inside_temperature_c >= 28.0 or environment.rain_probability >= 60.0


def defoliation_is_excessive(
    state: GreenhouseState,
    removal_ratio: float,
    leaf_density: float,
) -> bool:
    leaf_count_low = state.leaf_count is not None and state.leaf_count <= 20
    leaf_area_low = state.leaf_area_proxy is not None and state.leaf_area_proxy < 0.5
    return removal_ratio >= 0.35 or leaf_density <= 0.3 or leaf_count_low or leaf_area_low


def solar_moisture_triggered(
    state: GreenhouseState,
    environment: GreenhouseEnvironment,
) -> bool:
    solar_hit = (
        environment.solar_integral_j_cm2 is not None
        and 100.0 <= environment.solar_integral_j_cm2 <= 150.0
    )
    vwc_hit = state.substrate_vwc_m3_m3 is not None and state.substrate_vwc_m3_m3 < 0.18
    return solar_hit or state.substrate_moisture_pct < 60.0 or vwc_hit


def confidence(warnings: list[str]) -> float:
    return clamp(1.0 - len(warnings) * 0.12)


def unique_tags(evidence_tags: list[EvidenceTag]) -> list[EvidenceTag]:
    return list(dict.fromkeys(evidence_tags))


def unique_warnings(warnings: list[str]) -> list[str]:
    return list(dict.fromkeys(warnings))


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))
