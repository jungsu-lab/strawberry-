import unittest

from libsbapi.decision_contract import CurrentGreenhouseState, PredictionResult
from libsbapi.evidence_rules import load_evidence_rules
from libsbapi.work_need_scorer import WorkNeedScorer


class WorkNeedScorerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scorer = WorkNeedScorer(load_evidence_rules())

    def test_predicted_low_substrate_moisture_makes_irrigation_high(self) -> None:
        scores = self.scorer.score(
            _state(root_zone_moisture=62.0, vpd=1.1, solar_radiation=520.0),
            predictions=(
                _usable_prediction("root_zone_moisture", current_value=62.0, predicted_value=44.0),
            ),
        )

        irrigation = _score(scores, "irrigation")
        self.assertGreaterEqual(irrigation.score, 70.0)
        self.assertEqual(irrigation.status, "recommend")
        self.assertGreater(irrigation.moisture_stress, 0.0)

    def test_predicted_high_ec_makes_nutrient_score_high(self) -> None:
        scores = self.scorer.score(
            _state(drain_ec=1.6),
            predictions=(
                _usable_prediction("drain_ec", current_value=1.6, predicted_value=2.8),
            ),
        )

        nutrient = _score(scores, "nutrient_ec_check")
        self.assertGreaterEqual(nutrient.score, 70.0)
        self.assertEqual(nutrient.status, "recommend")
        self.assertGreater(nutrient.salinity_stress, 0.0)

    def test_predicted_high_humidity_and_low_vpd_makes_ventilation_high(self) -> None:
        scores = self.scorer.score(
            _state(humidity=76.0, vpd=0.7),
            predictions=(
                _usable_prediction("humidity", current_value=76.0, predicted_value=91.0),
                _usable_prediction("vpd", current_value=0.7, predicted_value=0.24),
            ),
        )

        ventilation = _score(scores, "ventilation_dehumidification")
        self.assertGreaterEqual(ventilation.score, 70.0)
        self.assertEqual(ventilation.status, "recommend")
        self.assertGreater(ventilation.disease_environment_risk, 0.0)

    def test_predicted_high_temperature_and_radiation_makes_shading_high(self) -> None:
        scores = self.scorer.score(
            _state(air_temp=25.0, solar_radiation=720.0, vpd=1.1),
            predictions=(
                _usable_prediction("air_temp", current_value=25.0, predicted_value=30.0),
            ),
        )

        shading = _score(scores, "shading_high_temperature")
        self.assertGreaterEqual(shading.score, 70.0)
        self.assertEqual(shading.status, "recommend")
        self.assertGreater(shading.high_temp_stress, 0.0)

    def test_predicted_low_night_temperature_makes_heating_high(self) -> None:
        scores = self.scorer.score(
            _state(air_temp=15.0, outside_temp=2.0, time_of_day="night"),
            predictions=(
                _usable_prediction("air_temp", current_value=15.0, predicted_value=8.5),
            ),
        )

        heating = _score(scores, "heating_low_temperature")
        self.assertGreaterEqual(heating.score, 70.0)
        self.assertEqual(heating.status, "recommend")
        self.assertGreater(heating.low_temp_stress, 0.0)
        self.assertGreater(heating.energy_cost, 0.0)

    def test_normal_conditions_have_no_urgent_scores(self) -> None:
        scores = self.scorer.score(
            _state(
                air_temp=23.0,
                humidity=72.0,
                vpd=0.8,
                solar_radiation=300.0,
                root_zone_moisture=58.0,
                drain_ec=1.4,
                outside_temp=12.0,
            )
        )

        self.assertTrue(all(item.score < 60.0 for item in scores))
        self.assertTrue(all(item.status in {"monitor", "hold"} for item in scores))

    def test_low_confidence_prediction_cannot_create_high_priority_score(self) -> None:
        scores = self.scorer.score(
            _state(root_zone_moisture=62.0),
            predictions=(
                PredictionResult(
                    target="root_zone_moisture",
                    horizon_hours=1,
                    current_value=62.0,
                    predicted_value=20.0,
                    predicted_delta=-42.0,
                    confidence=0.2,
                    model_used="weak_model",
                    fallback_used=True,
                    fallback_reason="low confidence",
                ),
            ),
        )

        irrigation = _score(scores, "irrigation")
        self.assertLess(irrigation.score, 70.0)
        self.assertNotEqual(irrigation.status, "recommend")


def _state(**kwargs) -> CurrentGreenhouseState:
    return CurrentGreenhouseState(timestamp="2026-06-25T09:00:00+09:00", **kwargs)


def _usable_prediction(target: str, current_value: float, predicted_value: float) -> PredictionResult:
    return PredictionResult(
        target=target,
        horizon_hours=1,
        current_value=current_value,
        predicted_value=predicted_value,
        predicted_delta=predicted_value - current_value,
        confidence=0.8,
        model_used="validated_delta_model",
        fallback_used=False,
        metrics=(
            ("training_rows", 240.0),
            ("validation_mae", 0.2),
            ("baseline_mae", 0.5),
            ("validation_r2", 0.2),
            ("missing_feature_ratio", 0.02),
        ),
    )


def _score(scores: tuple, action_type: str):
    matches = [item for item in scores if item.action_type == action_type]
    if len(matches) != 1:
        raise AssertionError(f"expected one score for {action_type}, got {len(matches)}")
    return matches[0]


if __name__ == "__main__":
    unittest.main()
