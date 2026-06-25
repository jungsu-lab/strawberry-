import unittest

from libsbapi.decision_contract import CurrentGreenhouseState
from libsbapi.evidence_rules import load_evidence_rules
from libsbapi.work_need_scorer import WorkNeedScorer


class ConfidenceLogicTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scorer = WorkNeedScorer(load_evidence_rules())

    def test_confidence_is_not_blindly_equal_for_missing_sensor_actions(self) -> None:
        scores = self.scorer.score(
            CurrentGreenhouseState(
                humidity=91.0,
                vpd=0.32,
                air_temp=29.0,
                solar_radiation=720.0,
                drain_ec=1.4,
            )
        )

        ventilation = _score(scores, "ventilation_dehumidification")
        nutrient = _score(scores, "nutrient_ec_check")
        shading = _score(scores, "shading_high_temperature")

        self.assertGreater(ventilation.confidence, nutrient.confidence)
        self.assertGreater(shading.confidence, nutrient.confidence)

    def test_missing_moisture_reduces_irrigation_confidence_more_than_complete_shading(self) -> None:
        scores = self.scorer.score(CurrentGreenhouseState(air_temp=30.0, solar_radiation=720.0, vpd=1.0))

        irrigation = _score(scores, "irrigation")
        shading = _score(scores, "shading_high_temperature")

        self.assertLess(irrigation.confidence, shading.confidence)
        self.assertTrue(irrigation.requires_human_review)

    def test_complete_data_has_higher_confidence_than_partial_data_for_same_action(self) -> None:
        complete = _score(
            self.scorer.score(CurrentGreenhouseState(feed_ec=1.2, drain_ec=1.4, root_ec=1.5)),
            "nutrient_ec_check",
        )
        partial = _score(self.scorer.score(CurrentGreenhouseState(drain_ec=1.4)), "nutrient_ec_check")
        missing = _score(self.scorer.score(CurrentGreenhouseState()), "nutrient_ec_check")

        self.assertGreater(complete.confidence, partial.confidence)
        self.assertGreater(partial.confidence, missing.confidence)

    def test_confidence_values_remain_bounded(self) -> None:
        scores = self.scorer.score(
            CurrentGreenhouseState(
                air_temp=24.0,
                humidity=72.0,
                vpd=0.8,
                solar_radiation=300.0,
                root_zone_moisture=62.0,
                feed_ec=1.2,
                drain_ec=1.4,
                root_ec=1.5,
            )
        )

        self.assertTrue(all(0.0 <= score.confidence <= 1.0 for score in scores))


def _score(scores: tuple, action_type: str):
    matches = [item for item in scores if item.action_type == action_type]
    if len(matches) != 1:
        raise AssertionError(f"expected one score for {action_type}, got {len(matches)}")
    return matches[0]


if __name__ == "__main__":
    unittest.main()
