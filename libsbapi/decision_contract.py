from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, TypeAlias


Priority: TypeAlias = str
ActionType: TypeAlias = str

PRIORITIES: Final = frozenset({"low", "medium", "high"})
ACTION_TYPES: Final = frozenset(
    {
        "irrigation",
        "nutrient_ec_check",
        "ph_check",
        "ventilation_dehumidification",
        "shading_high_temperature",
        "heating_low_temperature",
        "disease_environment_risk_proxy",
        "harvest_monitoring",
        "leaf_removal_caution",
        "ec_adjustment",
        "ph_adjustment",
        "ventilation",
        "shading",
        "heating",
        "disease_scouting",
        "disease_control",
        "harvest",
        "leaf_pruning",
        "monitor",
    }
)


@dataclass(frozen=True, slots=True)
class DecisionContractError(ValueError):
    field_name: str
    detail: str

    def __str__(self) -> str:
        return f"{self.field_name}: {self.detail}"


@dataclass(frozen=True, slots=True)
class SensorState:
    temperature_c: float | None = None
    humidity_pct: float | None = None
    vpd_kpa: float | None = None
    radiation_w_m2: float | None = None
    cumulative_radiation_j_cm2: float | None = None
    co2_ppm: float | None = None

    def __post_init__(self) -> None:
        _check_pct("humidity_pct", self.humidity_pct)
        _check_non_negative("vpd_kpa", self.vpd_kpa)
        _check_non_negative("radiation_w_m2", self.radiation_w_m2)
        _check_non_negative("cumulative_radiation_j_cm2", self.cumulative_radiation_j_cm2)
        _check_non_negative("co2_ppm", self.co2_ppm)


@dataclass(frozen=True, slots=True)
class RootZoneState:
    substrate_moisture_pct: float | None = None
    root_zone_ec: float | None = None
    root_zone_ph: float | None = None

    def __post_init__(self) -> None:
        _check_pct("substrate_moisture_pct", self.substrate_moisture_pct)
        _check_non_negative("root_zone_ec", self.root_zone_ec)
        _check_ph("root_zone_ph", self.root_zone_ph)


@dataclass(frozen=True, slots=True)
class NutrientState:
    drainage_ec: float | None = None
    drainage_ph: float | None = None
    feed_ec: float | None = None
    feed_ph: float | None = None
    drainage_ratio_pct: float | None = None

    def __post_init__(self) -> None:
        _check_non_negative("drainage_ec", self.drainage_ec)
        _check_ph("drainage_ph", self.drainage_ph)
        _check_non_negative("feed_ec", self.feed_ec)
        _check_ph("feed_ph", self.feed_ph)
        _check_pct("drainage_ratio_pct", self.drainage_ratio_pct)


@dataclass(frozen=True, slots=True)
class WeatherState:
    rain_probability_pct: float | None = None
    expected_rain_mm: float | None = None
    outside_temperature_c: float | None = None
    outside_humidity_pct: float | None = None

    def __post_init__(self) -> None:
        _check_pct("rain_probability_pct", self.rain_probability_pct)
        _check_non_negative("expected_rain_mm", self.expected_rain_mm)
        _check_pct("outside_humidity_pct", self.outside_humidity_pct)


@dataclass(frozen=True, slots=True)
class GrowthState:
    growth_stage: str | None = None
    fruit_count: int | None = None
    ripe_fruit_ratio: float | None = None
    leaf_density: float | None = None
    disease_spot_ratio: float | None = None

    def __post_init__(self) -> None:
        if self.fruit_count is not None and self.fruit_count < 0:
            raise DecisionContractError("fruit_count", "must be non-negative")
        _check_unit_interval("ripe_fruit_ratio", self.ripe_fruit_ratio)
        _check_unit_interval("leaf_density", self.leaf_density)
        _check_unit_interval("disease_spot_ratio", self.disease_spot_ratio)


@dataclass(frozen=True, slots=True)
class WorkHistoryEvent:
    timestamp: str
    action_type: str
    source: str
    notes: str = ""

    def __post_init__(self) -> None:
        _check_required("timestamp", self.timestamp)
        _check_required("action_type", self.action_type)
        _check_required("source", self.source)


@dataclass(frozen=True, slots=True)
class GreenhouseSnapshot:
    timestamp: str
    sensor_state: SensorState
    root_zone_state: RootZoneState = field(default_factory=RootZoneState)
    nutrient_state: NutrientState = field(default_factory=NutrientState)
    weather_state: WeatherState = field(default_factory=WeatherState)
    growth_state: GrowthState = field(default_factory=GrowthState)
    recent_work_history: tuple[WorkHistoryEvent, ...] = ()

    def __post_init__(self) -> None:
        _check_required("timestamp", self.timestamp)

    @property
    def temperature_c(self) -> float | None:
        return self.sensor_state.temperature_c

    @property
    def humidity_pct(self) -> float | None:
        return self.sensor_state.humidity_pct

    @property
    def vpd_kpa(self) -> float | None:
        return self.sensor_state.vpd_kpa

    @property
    def radiation_w_m2(self) -> float | None:
        return self.sensor_state.radiation_w_m2

    @property
    def cumulative_radiation_j_cm2(self) -> float | None:
        return self.sensor_state.cumulative_radiation_j_cm2

    @property
    def co2_ppm(self) -> float | None:
        return self.sensor_state.co2_ppm

    @property
    def substrate_moisture_pct(self) -> float | None:
        return self.root_zone_state.substrate_moisture_pct

    @property
    def root_zone_ec(self) -> float | None:
        return self.root_zone_state.root_zone_ec

    @property
    def root_zone_ph(self) -> float | None:
        return self.root_zone_state.root_zone_ph

    @property
    def drainage_ec(self) -> float | None:
        return self.nutrient_state.drainage_ec

    @property
    def drainage_ph(self) -> float | None:
        return self.nutrient_state.drainage_ph

    @property
    def growth_stage(self) -> str | None:
        return self.growth_state.growth_stage


@dataclass(frozen=True, slots=True)
class ActionCandidate:
    action_type: ActionType
    target_window: str
    rationale: str
    constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_action_type(self.action_type)
        _check_required("target_window", self.target_window)
        _check_required("rationale", self.rationale)


@dataclass(frozen=True, slots=True)
class PredictionResult:
    target: str
    horizon_hours: int
    predicted_value: float | None
    predicted_delta: float | None
    confidence: float
    model_used: str
    fallback_used: bool = False
    metrics: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        _check_required("target", self.target)
        if self.horizon_hours <= 0:
            raise DecisionContractError("horizon_hours", "must be positive")
        _check_unit_interval("confidence", self.confidence)
        _check_required("model_used", self.model_used)


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    source_type: str
    title: str
    reference_id: str
    url: str | None = None
    note: str = ""
    confidence: float = 1.0

    def __post_init__(self) -> None:
        _check_required("source_type", self.source_type)
        _check_required("title", self.title)
        _check_required("reference_id", self.reference_id)
        _check_unit_interval("confidence", self.confidence)


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    action_type: ActionType
    priority: Priority
    confidence: float
    reason: str
    expected_effect: str
    risks: tuple[str, ...]
    evidence_references: tuple[EvidenceReference, ...]
    safety_flags: tuple[str, ...]
    model_used: str
    fallback_used: bool
    action_candidate: ActionCandidate | None = None
    prediction: PredictionResult | None = None

    def __post_init__(self) -> None:
        _check_action_type(self.action_type)
        _check_priority(self.priority)
        _check_unit_interval("confidence", self.confidence)
        _check_required("reason", self.reason)
        _check_required("expected_effect", self.expected_effect)
        _check_required("model_used", self.model_used)


@dataclass(frozen=True, slots=True)
class DecisionContractSample:
    snapshot: GreenhouseSnapshot
    action_candidates: tuple[ActionCandidate, ...]
    predictions: tuple[PredictionResult, ...]
    recommendation: RecommendationResult


def _check_required(field_name: str, value: str) -> None:
    if value.strip() == "":
        raise DecisionContractError(field_name, "is required")


def _check_pct(field_name: str, value: float | None) -> None:
    if value is not None and not 0.0 <= value <= 100.0:
        raise DecisionContractError(field_name, "must be between 0 and 100")


def _check_unit_interval(field_name: str, value: float | None) -> None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise DecisionContractError(field_name, "must be between 0 and 1")


def _check_non_negative(field_name: str, value: float | None) -> None:
    if value is not None and value < 0.0:
        raise DecisionContractError(field_name, "must be non-negative")


def _check_ph(field_name: str, value: float | None) -> None:
    if value is not None and not 0.0 <= value <= 14.0:
        raise DecisionContractError(field_name, "must be between 0 and 14")


def _check_action_type(action_type: str) -> None:
    if action_type not in ACTION_TYPES:
        raise DecisionContractError("action_type", f"unsupported action type: {action_type}")


def _check_priority(priority: str) -> None:
    if priority not in PRIORITIES:
        raise DecisionContractError("priority", f"unsupported priority: {priority}")
