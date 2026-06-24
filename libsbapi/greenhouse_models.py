from dataclasses import dataclass
from enum import StrEnum, unique


@unique
class DistributionType(StrEnum):
    ROOM_TEMP = "room_temp"
    COLD_CHAIN = "cold_chain"
    LOW_TEMP = "low_temp"


@unique
class DiseaseControlMethod(StrEnum):
    FUNGICIDE = "fungicide"
    OZONATED_WATER = "ozonated_water"
    SCOUTING = "scouting"


@unique
class EvidenceTag(StrEnum):
    IRRIGATION_TRANSPIRATION = "irrigation_transpiration"
    IRRIGATION_SOLAR_MOISTURE = "irrigation_solar_moisture"
    IRRIGATION_VWC_SENSOR = "irrigation_vwc_sensor"
    IRRIGATION_EC_DRAINAGE = "irrigation_ec_drainage"
    NUTRIENT_SEOLHYANG_EC = "nutrient_seolhyang_ec"
    DISEASE_BOTRYTIS_FLOWERING = "disease_botrytis_flowering"
    DISEASE_ADVISORY_SYSTEM = "disease_advisory_system"
    HARVEST_SEOLHYANG_COLORING = "harvest_seolhyang_coloring"
    CANOPY_RUNNER_REMOVAL = "canopy_runner_removal"
    CANOPY_DEFOLIATION_LIMIT = "canopy_defoliation_limit"


@dataclass(frozen=True, slots=True)
class GreenhouseEnvironment:
    solar_radiation_w_m2: float
    vpd_kpa: float
    humidity_pct: float
    rain_probability: float
    inside_temperature_c: float
    solar_integral_j_cm2: float | None = None
    leaf_wetness_hours: float | None = None
    storage_temp_c: float | None = None
    month: int | None = None


@dataclass(frozen=True, slots=True)
class GreenhouseState:
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
    feed_ec: float | None = None
    drainage_ratio_pct: float | None = None
    substrate_vwc_m3_m3: float | None = None
    coloring_pct: float | None = None
    distribution_type: DistributionType = DistributionType.ROOM_TEMP
    runner_count: int = 0
    flower_count: int = 0
    leaf_count: int | None = None
    leaf_area_proxy: float | None = None
    flowering_stage_pct: float | None = None
    days_since_fungicide: int | None = None
    old_or_diseased_leaf_level: float = 0.0


@dataclass(frozen=True, slots=True)
class IrrigationWork:
    volume_l: float


@dataclass(frozen=True, slots=True)
class DiseaseControlWork:
    effectiveness: float
    method: DiseaseControlMethod = DiseaseControlMethod.FUNGICIDE


@dataclass(frozen=True, slots=True)
class HarvestWork:
    pick_ratio: float
    delayed_days: int = 0


@dataclass(frozen=True, slots=True)
class LeafPruningWork:
    removal_ratio: float


@dataclass(frozen=True, slots=True)
class RunnerRemovalWork:
    remove_count: int


@dataclass(frozen=True, slots=True)
class SimulationStep:
    state: GreenhouseState
    notes: tuple[str, ...]
    evidence_tags: tuple[EvidenceTag, ...] = ()
    warnings: tuple[str, ...] = ()
    metrics: tuple[tuple[str, float], ...] = ()
    confidence: float = 1.0
