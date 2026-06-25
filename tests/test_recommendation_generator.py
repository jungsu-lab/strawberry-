import unittest

from libsbapi.decision_contract import PredictionResult, WorkNeedScore
from libsbapi.recommendation_generator import RecommendationGenerator
from libsbapi.scenario_comparison import ShortHorizonScenarioResult


class RecommendationGeneratorTest(unittest.TestCase):
    def test_ranked_output_orders_higher_scores_first(self) -> None:
        report = RecommendationGenerator().generate(
            work_need_scores=(
                _score("irrigation", 42.0),
                _score("ventilation_dehumidification", 91.0),
                _score("shading_high_temperature", 74.0),
            )
        )

        self.assertEqual([item.action for item in report.level1_recommendations], [
            "ventilation_dehumidification",
            "shading_high_temperature",
            "irrigation",
        ])
        self.assertIn("1순위: 환기", report.to_korean_text())

    def test_hold_recommendations_include_reasons(self) -> None:
        report = RecommendationGenerator().generate(
            work_need_scores=(
                _score("irrigation", 34.0, moisture_stress=12.0),
            )
        )

        recommendation = report.level1_recommendations[0]
        self.assertEqual(recommendation.status, "hold")
        self.assertTrue(recommendation.reasons)
        self.assertIn("보류", report.to_korean_text())

    def test_level2_alerts_are_separated_from_level1_actions(self) -> None:
        report = RecommendationGenerator().generate(
            work_need_scores=(_score("ventilation_dehumidification", 80.0),),
            auxiliary_alerts=(
                _alert("disease_environment_risk_proxy", 63.0),
                _alert("harvest_monitoring", 51.0),
            ),
        )

        self.assertEqual(len(report.level1_recommendations), 1)
        self.assertEqual([item.action for item in report.auxiliary_alerts], [
            "disease_environment_risk_proxy",
            "harvest_monitoring",
        ])
        self.assertNotIn("disease_environment_risk_proxy", [item.action for item in report.level1_recommendations])

    def test_every_output_is_decision_support_and_human_reviewed(self) -> None:
        report = RecommendationGenerator().generate(
            work_need_scores=(_score("shading_high_temperature", 74.0),)
        )
        payload = report.to_json()

        item = payload["level1_recommendations"][0]
        self.assertEqual(item["mode"], "decision_support")
        self.assertTrue(item["requires_human_review"])

    def test_output_does_not_claim_autonomous_control(self) -> None:
        report = RecommendationGenerator().generate(
            work_need_scores=(_score("heating_low_temperature", 78.0),)
        )
        text = report.to_korean_text()

        self.assertNotIn("자동 제어", text)
        self.assertNotIn("제어 명령", text)
        self.assertIn("검토", text)

    def test_missing_predictions_are_shown_as_baseline_fallback(self) -> None:
        report = RecommendationGenerator().generate(
            work_need_scores=(_score("irrigation", 40.0),),
            predictions=(
                PredictionResult(
                    target="root_zone_moisture",
                    horizon_hours=1,
                    current_value=58.0,
                    predicted_delta=0.0,
                    confidence=0.2,
                    model_used="no_change_baseline",
                    fallback_used=True,
                    fallback_reason="no-change baseline",
                ),
            ),
        )

        text = report.to_korean_text()
        self.assertIn("baseline/fallback", report.level1_recommendations[0].prediction_refs[0])
        self.assertIn("baseline", text)

    def test_prediction_refs_are_limited_to_action_related_targets(self) -> None:
        report = RecommendationGenerator().generate(
            work_need_scores=(_score("irrigation", 72.0),),
            predictions=(
                PredictionResult(
                    target="root_zone_moisture",
                    horizon_hours=1,
                    current_value=42.0,
                    predicted_delta=-4.0,
                    confidence=0.72,
                    model_used="rolling_delta_baseline",
                ),
                PredictionResult(
                    target="drain_ec",
                    horizon_hours=1,
                    current_value=2.9,
                    predicted_delta=0.2,
                    confidence=0.72,
                    model_used="rolling_delta_baseline",
                ),
            ),
        )

        refs = report.level1_recommendations[0].prediction_refs
        self.assertTrue(any("root_zone_moisture" in ref for ref in refs))
        self.assertFalse(any("drain_ec" in ref for ref in refs))

    def test_scenario_notes_are_included(self) -> None:
        report = RecommendationGenerator().generate(
            work_need_scores=(_score("ventilation_dehumidification", 80.0),),
            scenario_results=(
                ShortHorizonScenarioResult(
                    action_type="ventilation",
                    horizon_hours=3,
                    moisture_delta=0.0,
                    ec_delta=0.0,
                    salinity_stress_delta=0.0,
                    humidity_delta=-9.0,
                    vpd_delta=0.24,
                    temperature_delta=-1.2,
                    disease_environment_risk_delta=-0.1,
                    energy_cost_delta=2.0,
                    confidence=0.48,
                    expected_benefits=("humidity and disease-environment risk proxy may decrease",),
                    risks=("temperature may drop if outside air is cold",),
                    warnings=("human review required before control changes",),
                    evidence_rule_ids=("environment.ventilation_dehumidification.001",),
                    evidence_tags=(),
                    notes=("heuristic prototype comparison only",),
                ),
            ),
        )

        item = report.level1_recommendations[0]
        self.assertTrue(item.simulation_refs)
        self.assertIn("humidity and disease-environment risk proxy may decrease", item.expected_effects)
        self.assertIn("습도와 병해 환경 위험 proxy가 낮아질 수 있습니다.", report.to_korean_text())
        self.assertNotIn("control changes", report.to_korean_text())


def _score(action_type: str, score: float, **components: float) -> WorkNeedScore:
    return WorkNeedScore(
        action_type=action_type,
        score=score,
        priority_rank=1,
        moisture_stress=components.get("moisture_stress", 0.0),
        salinity_stress=components.get("salinity_stress", 0.0),
        high_temp_stress=components.get("high_temp_stress", 0.0),
        low_temp_stress=components.get("low_temp_stress", 0.0),
        disease_environment_risk=components.get("disease_environment_risk", 0.0),
        energy_cost=components.get("energy_cost", 0.0),
        confidence=0.62,
        requires_human_review=True,
    )


def _alert(action_type: str, score: float) -> WorkNeedScore:
    return WorkNeedScore(
        action_type=action_type,
        score=score,
        priority_rank=10,
        disease_environment_risk=score if action_type == "disease_environment_risk_proxy" else 0.0,
        confidence=0.42,
        requires_human_review=True,
    )


if __name__ == "__main__":
    unittest.main()
