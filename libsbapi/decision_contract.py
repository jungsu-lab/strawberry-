from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, TypeAlias


Priority: TypeAlias = str
ActionType: TypeAlias = str
RecommendationStatus: TypeAlias = str
DecisionMode: TypeAlias = str

PRIORITIES: Final = frozenset({"low", "medium", "high"})
RECOMMENDATION_STATUSES: Final = frozenset({"recommend", "caution", "hold", "monitor"})
DECISION_SUPPORT_MODE: Final = "decision_support"
ACTION_TYPES: Final = frozenset(
    {
        "irrigation",
        "no_irrigation",
        "nutrient_ec_check",
        "ph_check",
        "ventilation_dehumidification",
        "no_ventilation",
        "shading_high_temperature",
        "no_shading",
        "heating_low_temperature",
        "heat_preservation_heating_review",
        "no_heat_preservation",
        "disease_environment_risk_proxy",
        "harvest_monitoring",
        "leaf_removal_caution",
        "ec_adjustment",
        "lower_ec_nutrient_adjustment",
        "raise_ec_check_supplied_ec",
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
WORK_NEED_COMPONENTS: Final = (
    "moisture_stress",
    "salinity_stress",
    "high_temp_stress",
    "low_temp_stress",
    "disease_environment_risk",
    "energy_cost",
)


@dataclass(frozen=True, slots=True)
class DecisionContractError(ValueError):
    field_name: str
    detail: str

    def __str__(self) -> str:
        return f"{self.field_name}: {self.detail}"


@dataclass(frozen=True, slots=True)
class CurrentGreenhouseState:
    """Model-independent current-state contract for the final BerryNext pipeline.

    The class intentionally contains only observed or normalized state fields.
    It does not encode agronomic thresholds or actuator commands.
    """

    timestamp: str | None = None
    air_temp: float | None = None
    humidity: float | None = None
    vpd: float | None = None
    co2: float | None = None
    solar_radiation: float | None = None
    cumulative_solar_radiation: float | None = None
    substrate_moisture: float | None = None
    root_zone_moisture: float | None = None
    feed_ec: float | None = None
    drain_ec: float | None = None
    root_ec: float | None = None
    feed_ph: float | None = None
    drain_ph: float | None = None
    drainage_ratio: float | None = None
    outside_temp: float | None = None
    outside_humidity: float | None = None
    growth_stage: str | None = None
    time_of_day: str | None = None
    sensor_quality: dict[str, str] = field(default_factory=dict)
    missing_fields: tuple[str, ...] = ()
    fallback_fields: tuple[str, ...] = ()
    suspicious_fields: tuple[str, ...] = ()
    assumed_units: dict[str, str] = field(default_factory=dict)
    stale_timestamp: bool | None = None
    source_labels: tuple[str, ...] = ()
    quality_warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.timestamp is not None:
            _check_required("timestamp", self.timestamp)
        _check_pct("humidity", self.humidity)
        _check_non_negative("vpd", self.vpd)
        _check_non_negative("co2", self.co2)
        _check_non_negative("solar_radiation", self.solar_radiation)
        _check_non_negative("cumulative_solar_radiation", self.cumulative_solar_radiation)
        _check_pct("substrate_moisture", self.substrate_moisture)
        _check_pct("root_zone_moisture", self.root_zone_moisture)
        _check_non_negative("feed_ec", self.feed_ec)
        _check_non_negative("drain_ec", self.drain_ec)
        _check_non_negative("root_ec", self.root_ec)
        _check_ph("feed_ph", self.feed_ph)
        _check_ph("drain_ph", self.drain_ph)
        _check_pct("drainage_ratio", self.drainage_ratio)
        _check_pct("outside_humidity", self.outside_humidity)
        if self.substrate_moisture is not None and self.root_zone_moisture is None:
            object.__setattr__(self, "root_zone_moisture", self.substrate_moisture)
        _check_str_mapping("sensor_quality", self.sensor_quality)
        _check_str_mapping("assumed_units", self.assumed_units)


@dataclass(frozen=True, slots=True)
class EnvironmentalPrediction:
    """Short-term environmental delta prediction result.

    `model_used` may be a baseline such as v0 no-change or v1 rolling delta.
    GAM can later produce the same contract without changing downstream code.
    """

    target: str
    horizon_hours: int
    current_value: float
    predicted_delta: float
    confidence: float
    model_used: str
    predicted_value: float | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    training_rows: int | None = None
    metric_summary: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_required("target", self.target)
        if self.horizon_hours <= 0:
            raise DecisionContractError("horizon_hours", "must be positive")
        _check_unit_interval("confidence", self.confidence)
        _check_required("model_used", self.model_used)
        if self.predicted_value is None:
            object.__setattr__(self, "predicted_value", self.current_value + self.predicted_delta)
        if self.training_rows is not None and self.training_rows < 0:
            raise DecisionContractError("training_rows", "must be non-negative")
        _check_metric_mapping("metric_summary", self.metric_summary)


@dataclass(frozen=True, slots=True)
class ScenarioCandidate:
    """Candidate action for what-if comparison, not an actuator command."""

    action_type: ActionType
    candidate_id: str
    description: str = ""
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_action_type(self.action_type)
        _check_required("candidate_id", self.candidate_id)


@dataclass(frozen=True, slots=True)
class WorkNeedScore:
    """0-100 work-need score used between rule scoring and recommendations."""

    action_type: ActionType
    score: float
    priority_rank: int
    moisture_stress: float = 0.0
    salinity_stress: float = 0.0
    high_temp_stress: float = 0.0
    low_temp_stress: float = 0.0
    disease_environment_risk: float = 0.0
    energy_cost: float = 0.0
    confidence: float = 1.0
    requires_human_review: bool = True

    def __post_init__(self) -> None:
        _check_action_type(self.action_type)
        _check_score_100("score", self.score)
        if self.priority_rank < 1:
            raise DecisionContractError("priority_rank", "must be positive")
        for component in WORK_NEED_COMPONENTS:
            _check_score_100(component, getattr(self, component))
        _check_unit_interval("confidence", self.confidence)

    @property
    def components(self) -> dict[str, float]:
        return {component: getattr(self, component) for component in WORK_NEED_COMPONENTS}

    @property
    def status(self) -> RecommendationStatus:
        if self.score >= 70.0:
            return "recommend"
        if self.score >= 55.0:
            return "caution"
        if self.score >= 30.0:
            return "hold"
        return "monitor"


@dataclass(frozen=True, slots=True)
class CoreRecommendation:
    """Final recommendation contract for human-reviewed decision support."""

    action: ActionType
    score: float
    priority: Priority
    status: RecommendationStatus
    reasons: tuple[str, ...]
    expected_effects: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    evidence_rule_ids: tuple[str, ...] = ()
    prediction_refs: tuple[str, ...] = ()
    simulation_refs: tuple[str, ...] = ()
    requires_human_review: bool = True
    mode: DecisionMode = DECISION_SUPPORT_MODE

    def __post_init__(self) -> None:
        _check_action_type(self.action)
        _check_score_100("score", self.score)
        _check_priority(self.priority)
        _check_recommendation_status(self.status)
        if not self.reasons:
            raise DecisionContractError("reasons", "must not be empty")
        if self.mode != DECISION_SUPPORT_MODE:
            raise DecisionContractError("mode", "must be decision_support")
        if not self.requires_human_review:
            raise DecisionContractError("requires_human_review", "must be true")


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
    confidence: float
    model_used: str
    predicted_value: float | None = None
    predicted_delta: float | None = None
    current_value: float | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    training_rows: int | None = None
    metrics: tuple[tuple[str, float], ...] = ()
    metric_summary: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_required("target", self.target)
        if self.horizon_hours <= 0:
            raise DecisionContractError("horizon_hours", "must be positive")
        _check_unit_interval("confidence", self.confidence)
        _check_required("model_used", self.model_used)
        if self.predicted_value is None and self.current_value is not None and self.predicted_delta is not None:
            object.__setattr__(self, "predicted_value", self.current_value + self.predicted_delta)
        if self.training_rows is not None and self.training_rows < 0:
            raise DecisionContractError("training_rows", "must be non-negative")
        _check_metric_items("metrics", self.metrics)
        _check_metric_mapping("metric_summary", self.metric_summary)


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
    requires_human_review: bool = True
    mode: DecisionMode = DECISION_SUPPORT_MODE

    def __post_init__(self) -> None:
        _check_action_type(self.action_type)
        _check_priority(self.priority)
        _check_unit_interval("confidence", self.confidence)
        _check_required("reason", self.reason)
        _check_required("expected_effect", self.expected_effect)
        _check_required("model_used", self.model_used)
        if self.mode != DECISION_SUPPORT_MODE:
            raise DecisionContractError("mode", "must be decision_support")
        if not self.requires_human_review:
            raise DecisionContractError("requires_human_review", "must be true")

    @property
    def action(self) -> ActionType:
        return self.action_type


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


def _check_score_100(field_name: str, value: float | None) -> None:
    if value is not None and not 0.0 <= value <= 100.0:
        raise DecisionContractError(field_name, "must be between 0 and 100")


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


def _check_recommendation_status(status: str) -> None:
    if status not in RECOMMENDATION_STATUSES:
        raise DecisionContractError("status", f"unsupported status: {status}")


def _check_metric_items(field_name: str, metrics: tuple[tuple[str, float], ...]) -> None:
    for key, value in metrics:
        _check_required(f"{field_name}.key", key)
        if isinstance(value, bool):
            raise DecisionContractError(f"{field_name}.{key}", "must be a number")
        if not isinstance(value, int | float):
            raise DecisionContractError(f"{field_name}.{key}", "must be a number")


def _check_metric_mapping(field_name: str, metrics: dict[str, float]) -> None:
    for key, value in metrics.items():
        _check_required(f"{field_name}.key", key)
        if isinstance(value, bool):
            raise DecisionContractError(f"{field_name}.{key}", "must be a number")
        if not isinstance(value, int | float):
            raise DecisionContractError(f"{field_name}.{key}", "must be a number")


def _check_str_mapping(field_name: str, values: dict[str, str]) -> None:
    for key, value in values.items():
        _check_required(f"{field_name}.key", key)
        _check_required(f"{field_name}.{key}", value)
