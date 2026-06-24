from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
from typing import Final

from libsbapi.decision_contract import PredictionResult, RecommendationResult


USABLE_MODEL: Final = "usable_model"
WEAK_MODEL_FALLBACK: Final = "weak_model_fallback"
INSUFFICIENT_DATA_FALLBACK: Final = "insufficient_data_fallback"
MISSING_TARGET_FALLBACK: Final = "missing_target_fallback"


@dataclass(frozen=True, slots=True)
class PredictionConfidenceError(ValueError):
    field_name: str
    detail: str

    def __str__(self) -> str:
        return f"{self.field_name}: {self.detail}"


def _check_ratio(field_name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise PredictionConfidenceError(field_name, "must be between 0 and 1")


def _check_non_negative(field_name: str, value: float) -> None:
    if value < 0.0:
        raise PredictionConfidenceError(field_name, "must be non-negative")


def _check_optional_non_negative(field_name: str, value: float | None) -> None:
    if value is not None and value < 0.0:
        raise PredictionConfidenceError(field_name, "must be non-negative")


@dataclass(frozen=True, slots=True)
class PredictionGateConfig:
    min_usable_rows: int = 100
    max_missing_feature_ratio: float = 0.35
    mae_tolerance: float = 0.0
    min_r2: float = 0.0
    usable_confidence_cap: float = 0.85
    weak_model_confidence: float = 0.35
    insufficient_data_confidence: float = 0.25
    missing_target_confidence: float = 0.2
    fallback_model_name: str = "literature_manual_rules"

    def __post_init__(self) -> None:
        if self.min_usable_rows < 1:
            raise PredictionConfidenceError("min_usable_rows", "must be positive")
        _check_ratio("max_missing_feature_ratio", self.max_missing_feature_ratio)
        _check_non_negative("mae_tolerance", self.mae_tolerance)
        _check_ratio("usable_confidence_cap", self.usable_confidence_cap)
        _check_ratio("weak_model_confidence", self.weak_model_confidence)
        _check_ratio("insufficient_data_confidence", self.insufficient_data_confidence)
        _check_ratio("missing_target_confidence", self.missing_target_confidence)
        if self.fallback_model_name.strip() == "":
            raise PredictionConfidenceError("fallback_model_name", "is required")


@dataclass(frozen=True, slots=True)
class PredictionGateInput:
    target: str | None
    usable_training_rows: int
    target_available: bool
    validation_mae: float | None
    baseline_mae: float | None
    validation_r2: float | None = None
    missing_feature_ratio: float = 0.0
    model_used: str = "unknown_model"
    model_confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.usable_training_rows < 0:
            raise PredictionConfidenceError("usable_training_rows", "must be non-negative")
        _check_optional_non_negative("validation_mae", self.validation_mae)
        _check_optional_non_negative("baseline_mae", self.baseline_mae)
        _check_ratio("missing_feature_ratio", self.missing_feature_ratio)
        if self.model_used.strip() == "":
            raise PredictionConfidenceError("model_used", "is required")


@dataclass(frozen=True, slots=True)
class PredictionGateDecision:
    status: str
    use_model: bool
    confidence: float
    safety_flags: tuple[str, ...]
    reason: str
    model_used: str
    fallback_used: bool


def evaluate_prediction_gate(
    gate_input: PredictionGateInput,
    config: PredictionGateConfig = PredictionGateConfig(),
) -> PredictionGateDecision:
    target = gate_input.target.strip() if gate_input.target else ""
    if not target or not gate_input.target_available:
        return _fallback_decision(
            status=MISSING_TARGET_FALLBACK,
            confidence=config.missing_target_confidence,
            reason="prediction target is missing or unavailable",
            model_used=config.fallback_model_name,
            flags=("missing_target", MISSING_TARGET_FALLBACK),
        )

    if gate_input.usable_training_rows < config.min_usable_rows:
        return _fallback_decision(
            status=INSUFFICIENT_DATA_FALLBACK,
            confidence=config.insufficient_data_confidence,
            reason="usable training rows are below the configured minimum",
            model_used=config.fallback_model_name,
            flags=("insufficient_training_rows", INSUFFICIENT_DATA_FALLBACK),
        )

    if gate_input.missing_feature_ratio > config.max_missing_feature_ratio:
        return _fallback_decision(
            status=INSUFFICIENT_DATA_FALLBACK,
            confidence=config.insufficient_data_confidence,
            reason="missing feature ratio is above the configured maximum",
            model_used=config.fallback_model_name,
            flags=("high_missing_feature_ratio", INSUFFICIENT_DATA_FALLBACK),
        )

    if gate_input.validation_mae is None or gate_input.baseline_mae is None:
        return _fallback_decision(
            status=WEAK_MODEL_FALLBACK,
            confidence=config.weak_model_confidence,
            reason="validation MAE and baseline MAE are required before model use",
            model_used=config.fallback_model_name,
            flags=("missing_validation_metrics", WEAK_MODEL_FALLBACK),
        )

    if gate_input.validation_mae >= gate_input.baseline_mae - config.mae_tolerance:
        return _fallback_decision(
            status=WEAK_MODEL_FALLBACK,
            confidence=config.weak_model_confidence,
            reason="validation MAE does not beat the simple baseline MAE",
            model_used=config.fallback_model_name,
            flags=("model_not_better_than_baseline", WEAK_MODEL_FALLBACK),
        )

    if gate_input.validation_r2 is not None and gate_input.validation_r2 < config.min_r2:
        return _fallback_decision(
            status=WEAK_MODEL_FALLBACK,
            confidence=config.weak_model_confidence,
            reason="validation R2 is below the configured minimum",
            model_used=config.fallback_model_name,
            flags=("low_validation_r2", WEAK_MODEL_FALLBACK),
        )

    confidence = min(gate_input.model_confidence, config.usable_confidence_cap)
    return PredictionGateDecision(
        status=USABLE_MODEL,
        use_model=True,
        confidence=confidence,
        safety_flags=(USABLE_MODEL,),
        reason="model passes data availability and baseline-comparison gates",
        model_used=gate_input.model_used,
        fallback_used=False,
    )


def prediction_gate_input_from_result(
    prediction: PredictionResult,
    *,
    usable_training_rows: int | None = None,
    target_available: bool = True,
    validation_mae: float | None = None,
    baseline_mae: float | None = None,
    validation_r2: float | None = None,
    missing_feature_ratio: float | None = None,
) -> PredictionGateInput:
    metrics = dict(prediction.metrics)
    rows = usable_training_rows
    if rows is None:
        rows = _metric_int(metrics, "usable_training_rows")
    if rows is None:
        rows = _metric_int(metrics, "training_rows")
    return PredictionGateInput(
        target=prediction.target,
        usable_training_rows=rows or 0,
        target_available=target_available,
        validation_mae=_value_or_metric(validation_mae, metrics, "validation_mae"),
        baseline_mae=_value_or_metric(baseline_mae, metrics, "baseline_mae"),
        validation_r2=_value_or_metric(validation_r2, metrics, "validation_r2"),
        missing_feature_ratio=_value_or_metric(
            missing_feature_ratio, metrics, "missing_feature_ratio"
        )
        or 0.0,
        model_used=prediction.model_used,
        model_confidence=prediction.confidence,
    )


def gate_prediction_result(
    prediction: PredictionResult,
    config: PredictionGateConfig = PredictionGateConfig(),
) -> PredictionGateDecision:
    return evaluate_prediction_gate(prediction_gate_input_from_result(prediction), config)


def apply_prediction_gate_to_recommendation(
    recommendation: RecommendationResult,
    gate_decision: PredictionGateDecision,
    config: PredictionGateConfig = PredictionGateConfig(),
) -> RecommendationResult:
    flags = _append_unique(recommendation.safety_flags, gate_decision.safety_flags)
    if gate_decision.use_model:
        return replace(
            recommendation,
            model_used=gate_decision.model_used,
            fallback_used=False,
            confidence=min(recommendation.confidence, gate_decision.confidence),
            safety_flags=flags,
        )

    risks = _append_unique(recommendation.risks, (gate_decision.reason,))
    return replace(
        recommendation,
        model_used=config.fallback_model_name,
        fallback_used=True,
        confidence=min(recommendation.confidence, gate_decision.confidence),
        risks=risks,
        safety_flags=_append_unique(flags, ("rule_based_fallback",)),
    )


def gate_recommendation_prediction(
    recommendation: RecommendationResult,
    config: PredictionGateConfig = PredictionGateConfig(),
) -> RecommendationResult:
    if recommendation.prediction is None:
        decision = _fallback_decision(
            status=MISSING_TARGET_FALLBACK,
            confidence=config.missing_target_confidence,
            reason="recommendation has no prediction result to gate",
            model_used=config.fallback_model_name,
            flags=("missing_prediction", MISSING_TARGET_FALLBACK),
        )
        return apply_prediction_gate_to_recommendation(recommendation, decision, config)

    decision = gate_prediction_result(recommendation.prediction, config)
    return apply_prediction_gate_to_recommendation(recommendation, decision, config)


def _fallback_decision(
    *,
    status: str,
    confidence: float,
    reason: str,
    model_used: str,
    flags: tuple[str, ...],
) -> PredictionGateDecision:
    return PredictionGateDecision(
        status=status,
        use_model=False,
        confidence=confidence,
        safety_flags=flags,
        reason=reason,
        model_used=model_used,
        fallback_used=True,
    )


def _metric_int(metrics: dict[str, float], key: str) -> int | None:
    value = metrics.get(key)
    if value is None or not isfinite(value) or value < 0:
        return None
    return int(value)


def _value_or_metric(
    value: float | None,
    metrics: dict[str, float],
    key: str,
) -> float | None:
    if value is not None:
        return value
    metric = metrics.get(key)
    if metric is None:
        return None
    return metric


def _append_unique(current: tuple[str, ...], additions: tuple[str, ...]) -> tuple[str, ...]:
    result = list(current)
    for item in additions:
        if item not in result:
            result.append(item)
    return tuple(result)
