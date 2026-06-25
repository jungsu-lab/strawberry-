from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .decision_contract import CurrentGreenhouseState, PredictionResult


PREDICT_TARGETS = (
    "air_temp",
    "humidity",
    "vpd",
    "solar_radiation",
    "root_zone_moisture",
    "drain_ec",
)
V0_CONFIDENCE = 0.2


class EnvironmentalPredictor(Protocol):
    def predict(
        self,
        current_state: CurrentGreenhouseState,
        history: Sequence[CurrentGreenhouseState] | None = None,
        horizons: Iterable[int] = (1, 2, 3),
    ) -> tuple[PredictionResult, ...]:
        """Predict short-term environmental deltas without producing actions."""


@dataclass(frozen=True, slots=True)
class NoChangeBaselinePredictor:
    confidence: float = V0_CONFIDENCE

    def predict(
        self,
        current_state: CurrentGreenhouseState,
        history: Sequence[CurrentGreenhouseState] | None = None,
        horizons: Iterable[int] = (1, 2, 3),
    ) -> tuple[PredictionResult, ...]:
        del history
        predictions: list[PredictionResult] = []
        for horizon in _valid_horizons(horizons):
            for target in PREDICT_TARGETS:
                current_value = _target_value(current_state, target)
                if current_value is None:
                    continue
                predictions.append(
                    PredictionResult(
                        target=target,
                        horizon_hours=horizon,
                        current_value=current_value,
                        predicted_delta=0.0,
                        predicted_value=current_value,
                        confidence=self.confidence,
                        model_used="no_change_baseline",
                        fallback_used=True,
                        fallback_reason="no-change baseline",
                    )
                )
        return tuple(predictions)


@dataclass(frozen=True, slots=True)
class RollingDeltaBaselinePredictor:
    min_history_points: int = 1

    def predict(
        self,
        current_state: CurrentGreenhouseState,
        history: Sequence[CurrentGreenhouseState] | None = None,
        horizons: Iterable[int] = (1, 2, 3),
    ) -> tuple[PredictionResult, ...]:
        recent_history = tuple(history or ())
        if len(recent_history) < self.min_history_points:
            return _as_rolling_fallback(NoChangeBaselinePredictor().predict(current_state, horizons=horizons))

        predictions: list[PredictionResult] = []
        for horizon in _valid_horizons(horizons):
            for target in PREDICT_TARGETS:
                current_value = _target_value(current_state, target)
                if current_value is None:
                    continue
                per_hour_delta = _rolling_delta_per_hour(target, current_state, recent_history)
                if per_hour_delta is None:
                    predictions.append(
                        _rolling_fallback_prediction(target, horizon, current_value, "target history unavailable")
                    )
                    continue
                predicted_delta = per_hour_delta * horizon
                predictions.append(
                    PredictionResult(
                        target=target,
                        horizon_hours=horizon,
                        current_value=current_value,
                        predicted_delta=round(predicted_delta, 6),
                        predicted_value=round(current_value + predicted_delta, 6),
                        confidence=_rolling_confidence(recent_history),
                        model_used="rolling_delta_baseline",
                        fallback_used=False,
                        training_rows=len(recent_history),
                        metric_summary={"history_points": float(len(recent_history))},
                    )
                )
        return tuple(predictions)


@dataclass(frozen=True, slots=True)
class GAMReadyPredictor:
    def predict(
        self,
        current_state: CurrentGreenhouseState,
        history: Sequence[CurrentGreenhouseState] | None = None,
        horizons: Iterable[int] = (1, 2, 3),
    ) -> tuple[PredictionResult, ...]:
        del current_state, history, horizons
        raise NotImplementedError("GAM environmental predictor is planned but not implemented")


def predict_environment_delta(
    current_state: CurrentGreenhouseState,
    history: Sequence[CurrentGreenhouseState] | None = None,
    horizons: Iterable[int] = (1, 2, 3),
    predictor: EnvironmentalPredictor | None = None,
) -> tuple[PredictionResult, ...]:
    selected_predictor = predictor or RollingDeltaBaselinePredictor()
    return selected_predictor.predict(current_state, history=history, horizons=horizons)


def _valid_horizons(horizons: Iterable[int]) -> tuple[int, ...]:
    result = tuple(horizon for horizon in horizons if horizon > 0)
    if not result:
        raise ValueError("horizons must contain at least one positive hour value")
    return result


def _target_value(state: CurrentGreenhouseState, target: str) -> float | None:
    value = getattr(state, target)
    return float(value) if value is not None else None


def _as_rolling_fallback(predictions: tuple[PredictionResult, ...]) -> tuple[PredictionResult, ...]:
    return tuple(
        PredictionResult(
            target=item.target,
            horizon_hours=item.horizon_hours,
            current_value=item.current_value,
            predicted_delta=item.predicted_delta,
            predicted_value=item.predicted_value,
            confidence=item.confidence,
            model_used="rolling_delta_baseline",
            fallback_used=True,
            fallback_reason="recent history unavailable; using no-change baseline",
        )
        for item in predictions
    )


def _rolling_fallback_prediction(
    target: str,
    horizon: int,
    current_value: float,
    reason: str,
) -> PredictionResult:
    return PredictionResult(
        target=target,
        horizon_hours=horizon,
        current_value=current_value,
        predicted_delta=0.0,
        predicted_value=current_value,
        confidence=V0_CONFIDENCE,
        model_used="rolling_delta_baseline",
        fallback_used=True,
        fallback_reason=f"{reason}; using no-change baseline",
    )


def _rolling_delta_per_hour(
    target: str,
    current_state: CurrentGreenhouseState,
    history: Sequence[CurrentGreenhouseState],
) -> float | None:
    points = [state for state in (*history, current_state) if _target_value(state, target) is not None]
    if len(points) < 2:
        return None
    deltas: list[float] = []
    for previous, current in zip(points, points[1:], strict=False):
        previous_value = _target_value(previous, target)
        current_value = _target_value(current, target)
        if previous_value is None or current_value is None:
            continue
        hours = _hours_between(previous.timestamp, current.timestamp)
        if hours is None or hours <= 0:
            hours = 1.0
        deltas.append((current_value - previous_value) / hours)
    if not deltas:
        return None
    return sum(deltas) / len(deltas)


def _hours_between(previous: str | None, current: str | None) -> float | None:
    previous_dt = _parse_datetime(previous)
    current_dt = _parse_datetime(current)
    if previous_dt is None or current_dt is None:
        return None
    return (current_dt - previous_dt).total_seconds() / 3600.0


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _rolling_confidence(history: Sequence[CurrentGreenhouseState]) -> float:
    return min(0.35 + 0.08 * len(history), 0.7)
