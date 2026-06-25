import unittest

from examples.berrynext_today_recommendation import build_demo


class CorrectedBerryNextPipelineRegressionTest(unittest.TestCase):
    LEVEL1_ACTIONS = {
        "irrigation",
        "nutrient_ec_check",
        "ventilation_dehumidification",
        "shading_high_temperature",
        "heating_low_temperature",
    }
    AUXILIARY_ACTIONS = {
        "disease_environment_risk_proxy",
        "harvest_monitoring",
        "leaf_removal_caution",
    }

    def test_offline_demo_protects_corrected_architecture_contract(self) -> None:
        demo = build_demo()
        report = demo.recommendation_report

        self.assertEqual({item.action for item in report.level1_recommendations}, self.LEVEL1_ACTIONS)
        self.assertEqual({item.action for item in report.auxiliary_alerts}, self.AUXILIARY_ACTIONS)
        self.assertFalse(
            {item.action for item in report.level1_recommendations}
            & {item.action for item in report.auxiliary_alerts}
        )

        self.assertTrue(all(item.mode == "decision_support" for item in report.level1_recommendations))
        self.assertTrue(all(item.requires_human_review for item in report.level1_recommendations))
        self.assertTrue(all(item.reasons for item in report.level1_recommendations))
        self.assertTrue(all(item.reasons for item in report.auxiliary_alerts))

        all_recommendations = (*report.level1_recommendations, *report.auxiliary_alerts)
        self.assertTrue(all(item.evidence_rule_ids for item in all_recommendations))
        self.assertFalse(
            any(rule_id.endswith(".score.prototype") for item in all_recommendations for rule_id in item.evidence_rule_ids)
        )

        self.assertEqual({item.horizon_hours for item in demo.predictions}, {1, 2, 3})
        self.assertTrue(all(item.model_used for item in demo.predictions))
        self.assertTrue(all(item.fallback_used is not None for item in demo.predictions))
        self.assertTrue(all(0.0 <= item.confidence <= 1.0 for item in demo.predictions))

        self.assertTrue(demo.scenario_report.scenarios)
        self.assertTrue(all(not item.is_training_label for item in demo.scenario_report.scenarios))
        self.assertIn("fake supervised", demo.scenario_report.not_training_label_notice)
        self.assertIn("아닙니다", demo.scenario_report.not_training_label_notice)


if __name__ == "__main__":
    unittest.main()
