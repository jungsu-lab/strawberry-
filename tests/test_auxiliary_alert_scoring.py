import unittest

from libsbapi.auxiliary_alert_scoring import auxiliary_alert_scores
from libsbapi.decision_contract import CurrentGreenhouseState


class AuxiliaryAlertScoringTest(unittest.TestCase):
    def test_high_humidity_low_vpd_creates_disease_proxy_alert(self) -> None:
        scores = auxiliary_alert_scores(
            CurrentGreenhouseState(humidity=91.0, vpd=0.28),
            {"snapshot": {"image": {}}},
        )

        self.assertIn("disease_environment_risk_proxy", [score.action_type for score in scores])

    def test_harvest_alert_requires_growth_or_image_proxy(self) -> None:
        scores = auxiliary_alert_scores(
            CurrentGreenhouseState(humidity=91.0, vpd=0.28, growth_stage="vegetative"),
            {"snapshot": {"image": {}}},
        )

        self.assertNotIn("harvest_monitoring", [score.action_type for score in scores])


if __name__ == "__main__":
    unittest.main()
