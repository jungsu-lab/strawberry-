import unittest

from libsbapi.decision_contract import CurrentGreenhouseState
from libsbapi.environmental_prediction import (
    GAMReadyPredictor,
    NoChangeBaselinePredictor,
    RollingDeltaBaselinePredictor,
    predict_environment_delta,
)


class EnvironmentalPredictionTest(unittest.TestCase):
    def test_v0_returns_zero_delta_and_current_value_for_all_horizons(self) -> None:
        current = _state(air_temp=24.0, humidity=80.0, vpd=0.62)

        predictions = NoChangeBaselinePredictor().predict(current, horizons=(1, 2, 3))
        by_target_horizon = {(item.target, item.horizon_hours): item for item in predictions}

        prediction = by_target_horizon[("air_temp", 2)]
        self.assertEqual(prediction.current_value, 24.0)
        self.assertEqual(prediction.predicted_delta, 0.0)
        self.assertEqual(prediction.predicted_value, 24.0)
        self.assertEqual(prediction.model_used, "no_change_baseline")
        self.assertTrue(prediction.fallback_used)
        self.assertEqual(prediction.fallback_reason, "no-change baseline")
        self.assertEqual(sorted({item.horizon_hours for item in predictions}), [1, 2, 3])

    def test_v1_uses_recent_history_to_estimate_delta(self) -> None:
        history = (
            _state(timestamp="2026-06-25T07:00:00+09:00", air_temp=20.0, humidity=86.0),
            _state(timestamp="2026-06-25T08:00:00+09:00", air_temp=21.0, humidity=84.0),
        )
        current = _state(timestamp="2026-06-25T09:00:00+09:00", air_temp=23.0, humidity=81.0)

        predictions = RollingDeltaBaselinePredictor().predict(current, history=history, horizons=(1, 3))
        by_target_horizon = {(item.target, item.horizon_hours): item for item in predictions}

        one_hour = by_target_horizon[("air_temp", 1)]
        three_hour = by_target_horizon[("air_temp", 3)]
        self.assertEqual(one_hour.model_used, "rolling_delta_baseline")
        self.assertFalse(one_hour.fallback_used)
        self.assertAlmostEqual(one_hour.predicted_delta or 0.0, 1.5)
        self.assertAlmostEqual(three_hour.predicted_delta or 0.0, 4.5)
        self.assertGreater(one_hour.confidence, 0.3)

    def test_v1_falls_back_to_v0_when_history_is_missing(self) -> None:
        current = _state(air_temp=22.0)

        predictions = RollingDeltaBaselinePredictor().predict(current, history=(), horizons=(1,))
        prediction = _single(predictions, "air_temp", 1)

        self.assertEqual(prediction.model_used, "rolling_delta_baseline")
        self.assertTrue(prediction.fallback_used)
        self.assertEqual(prediction.fallback_reason, "recent history unavailable; using no-change baseline")
        self.assertEqual(prediction.predicted_delta, 0.0)
        self.assertEqual(prediction.predicted_value, 22.0)

    def test_missing_current_value_is_handled_safely(self) -> None:
        current = _state(air_temp=None, humidity=80.0)

        predictions = NoChangeBaselinePredictor().predict(current, horizons=(1,))
        targets = {item.target for item in predictions}

        self.assertNotIn("air_temp", targets)
        self.assertIn("humidity", targets)

    def test_predict_environment_delta_defaults_to_rolling_baseline(self) -> None:
        current = _state(air_temp=24.0, root_zone_moisture=45.0, drain_ec=1.6)

        predictions = predict_environment_delta(current, horizons=(1, 2, 3))

        self.assertEqual(sorted({item.horizon_hours for item in predictions}), [1, 2, 3])
        self.assertIn("root_zone_moisture", {item.target for item in predictions})
        self.assertIn("drain_ec", {item.target for item in predictions})

    def test_gam_ready_predictor_is_placeholder_only(self) -> None:
        with self.assertRaises(NotImplementedError):
            GAMReadyPredictor().predict(_state(air_temp=24.0), horizons=(1,))


def _state(
    timestamp: str = "2026-06-25T09:00:00+09:00",
    air_temp: float | None = None,
    humidity: float | None = None,
    vpd: float | None = None,
    solar_radiation: float | None = None,
    root_zone_moisture: float | None = None,
    drain_ec: float | None = None,
) -> CurrentGreenhouseState:
    return CurrentGreenhouseState(
        timestamp=timestamp,
        air_temp=air_temp,
        humidity=humidity,
        vpd=vpd,
        solar_radiation=solar_radiation,
        root_zone_moisture=root_zone_moisture,
        drain_ec=drain_ec,
    )


def _single(predictions: tuple, target: str, horizon: int):
    matches = [item for item in predictions if item.target == target and item.horizon_hours == horizon]
    if len(matches) != 1:
        raise AssertionError(f"expected one prediction for {target}/{horizon}, got {len(matches)}")
    return matches[0]


if __name__ == "__main__":
    unittest.main()
