import unittest

from libsbapi.decision_contract import CurrentGreenhouseState
from libsbapi.evidence_rules import load_evidence_rules
from libsbapi.recommendation_generator import RecommendationGenerator
from libsbapi.work_need_scorer import WorkNeedScorer


class RecommendationSanityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = load_evidence_rules()
        self.scorer = WorkNeedScorer(self.rules)

    def test_wet_low_vpd_adequate_moisture_prioritizes_ventilation_not_irrigation(self) -> None:
        report = self._report(
            CurrentGreenhouseState(
                humidity=90.0,
                vpd=0.32,
                root_zone_moisture=66.0,
                solar_radiation=350.0,
                air_temp=24.0,
            )
        )

        ventilation = _recommendation(report, "ventilation_dehumidification")
        irrigation = _recommendation(report, "irrigation")

        self.assertGreaterEqual(ventilation.score, 70.0)
        self.assertLess(irrigation.score, ventilation.score)
        self.assertIn(irrigation.status, {"hold", "monitor", "caution"})
        self.assertInAny(("과습", "병해 환경"), irrigation.reasons)

    def test_low_moisture_high_vpd_recommends_irrigation_with_clear_reason(self) -> None:
        report = self._report(
            CurrentGreenhouseState(
                humidity=58.0,
                vpd=1.35,
                root_zone_moisture=38.0,
                solar_radiation=520.0,
                air_temp=26.0,
            )
        )

        irrigation = _recommendation(report, "irrigation")

        self.assertGreaterEqual(irrigation.score, 70.0)
        self.assertIn(irrigation.status, {"recommend", "caution"})
        self.assertInAny(("수분", "VPD"), irrigation.reasons)

    def test_high_drain_ec_recommends_ec_nutrient_adjustment(self) -> None:
        report = self._report(CurrentGreenhouseState(feed_ec=1.2, drain_ec=2.8, root_ec=2.7))

        nutrient = _recommendation(report, "nutrient_ec_check")

        self.assertGreaterEqual(nutrient.score, 70.0)
        self.assertIn("EC", " ".join(nutrient.reasons))
        self.assertInAny(("염류", "축적"), nutrient.reasons)

    def test_missing_root_or_drain_ec_lowers_ec_confidence(self) -> None:
        full = _score(self.scorer.score(CurrentGreenhouseState(feed_ec=1.2, drain_ec=1.4, root_ec=1.5)), "nutrient_ec_check")
        missing = _score(self.scorer.score(CurrentGreenhouseState(feed_ec=1.2)), "nutrient_ec_check")

        self.assertLess(missing.confidence, full.confidence)
        self.assertTrue(missing.requires_human_review)

    def test_high_humidity_low_vpd_recommends_ventilation_without_disease_prediction_claim(self) -> None:
        report = self._report(CurrentGreenhouseState(humidity=92.0, vpd=0.28, air_temp=24.0))

        ventilation = _recommendation(report, "ventilation_dehumidification")
        text = " ".join((*ventilation.reasons, *ventilation.risks))

        self.assertGreaterEqual(ventilation.score, 70.0)
        self.assertInAny(("결로", "병해 환경"), ventilation.reasons)
        self.assertNotIn("병해 예측", text)
        self.assertNotIn("진단", text)

    def test_high_temperature_high_radiation_recommends_shading(self) -> None:
        report = self._report(CurrentGreenhouseState(air_temp=31.0, solar_radiation=760.0, vpd=1.0))

        shading = _recommendation(report, "shading_high_temperature")

        self.assertGreaterEqual(shading.score, 70.0)
        self.assertInAny(("고온", "고일사", "일사"), shading.reasons)

    def test_low_night_temperature_recommends_heating_with_energy_warning(self) -> None:
        report = self._report(CurrentGreenhouseState(air_temp=9.0, outside_temp=1.0, time_of_day="night"))

        heating = _recommendation(report, "heating_low_temperature")

        self.assertGreaterEqual(heating.score, 70.0)
        self.assertInAny(("저온", "야간"), heating.reasons)
        self.assertInAny(("에너지", "비용"), (*heating.reasons, *heating.risks))

    def test_normal_conditions_have_no_urgent_level1_recommendations(self) -> None:
        report = self._report(
            CurrentGreenhouseState(
                air_temp=23.0,
                humidity=72.0,
                vpd=0.8,
                solar_radiation=300.0,
                root_zone_moisture=62.0,
                feed_ec=1.2,
                drain_ec=1.4,
                root_ec=1.5,
            )
        )

        self.assertTrue(all(item.score < 70.0 for item in report.level1_recommendations))
        self.assertTrue(all(item.status in {"monitor", "hold", "caution"} for item in report.level1_recommendations))
        self.assertTrue(all(item.reasons for item in report.level1_recommendations))

    def test_missing_required_sensors_lower_confidence_and_keep_human_review(self) -> None:
        complete = _score(
            self.scorer.score(CurrentGreenhouseState(root_zone_moisture=62.0, humidity=70.0, vpd=0.8, solar_radiation=300.0)),
            "irrigation",
        )
        missing = _score(self.scorer.score(CurrentGreenhouseState(humidity=70.0, vpd=0.8)), "irrigation")

        self.assertLess(missing.confidence, complete.confidence)
        self.assertTrue(missing.requires_human_review)

    def _report(self, state: CurrentGreenhouseState):
        scores = self.scorer.score(state)
        return RecommendationGenerator().generate(work_need_scores=scores, evidence_rules=self.rules)


def _score(scores: tuple, action_type: str):
    matches = [item for item in scores if item.action_type == action_type]
    if len(matches) != 1:
        raise AssertionError(f"expected one score for {action_type}, got {len(matches)}")
    return matches[0]


def _recommendation(report, action_type: str):
    matches = [item for item in report.level1_recommendations if item.action == action_type]
    if len(matches) != 1:
        raise AssertionError(f"expected one recommendation for {action_type}, got {len(matches)}")
    return matches[0]


def _assert_in_any(self, needles: tuple[str, ...], haystack: tuple[str, ...]) -> None:
    text = " ".join(haystack)
    if not any(needle in text for needle in needles):
        raise AssertionError(f"expected one of {needles!r} in {text!r}")


unittest.TestCase.assertInAny = _assert_in_any


if __name__ == "__main__":
    unittest.main()
