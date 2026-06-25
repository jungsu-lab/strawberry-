import unittest
from dataclasses import asdict

from libsbapi.decision_contract import (
    CoreRecommendation,
    CurrentGreenhouseState,
    DecisionContractError,
    EvidenceReference,
    EnvironmentalPrediction,
    RecommendationResult,
    ScenarioCandidate,
    WorkNeedScore,
)


class CoreDecisionContractsTest(unittest.TestCase):
    def test_current_state_supports_final_pipeline_fields(self) -> None:
        state = CurrentGreenhouseState(
            timestamp="2026-06-25T09:00:00+09:00",
            air_temp=24.5,
            humidity=78.0,
            vpd=0.72,
            co2=610.0,
            solar_radiation=420.0,
            cumulative_solar_radiation=830.0,
            substrate_moisture=54.0,
            feed_ec=1.2,
            drain_ec=1.9,
            root_ec=1.7,
            feed_ph=5.8,
            drain_ph=6.2,
            drainage_ratio=38.0,
            outside_temp=13.0,
            outside_humidity=84.0,
            growth_stage="fruiting",
            time_of_day="morning",
            sensor_quality={"air_temp": "ok", "drain_ec": "estimated"},
        )

        self.assertEqual(state.air_temp, 24.5)
        self.assertEqual(state.substrate_moisture, 54.0)
        self.assertEqual(state.root_zone_moisture, 54.0)
        self.assertEqual(state.sensor_quality["drain_ec"], "estimated")
        self.assertEqual(asdict(state)["growth_stage"], "fruiting")

    def test_environmental_prediction_derives_predicted_value_from_delta(self) -> None:
        prediction = EnvironmentalPrediction(
            target="humidity",
            horizon_hours=3,
            current_value=78.0,
            predicted_delta=5.5,
            confidence=0.61,
            model_used="v1_rolling_delta_baseline",
            fallback_used=True,
            fallback_reason="GAM not implemented",
            training_rows=240,
            metric_summary={"mae": 3.2},
        )

        self.assertEqual(prediction.predicted_value, 83.5)
        self.assertEqual(prediction.metric_summary["mae"], 3.2)

    def test_scenario_candidate_supports_required_action_set(self) -> None:
        required_actions = (
            "irrigation",
            "no_irrigation",
            "lower_ec_nutrient_adjustment",
            "raise_ec_check_supplied_ec",
            "ventilation",
            "no_ventilation",
            "shading",
            "no_shading",
            "heat_preservation_heating_review",
            "no_heat_preservation",
        )

        candidates = tuple(
            ScenarioCandidate(action_type=action, candidate_id=f"{index}")
            for index, action in enumerate(required_actions)
        )

        self.assertEqual(candidates[0].action_type, "irrigation")
        self.assertEqual(candidates[-1].action_type, "no_heat_preservation")

    def test_work_need_score_rejects_scores_outside_zero_to_one_hundred(self) -> None:
        score = WorkNeedScore(
            action_type="irrigation",
            score=74.0,
            priority_rank=1,
            moisture_stress=80.0,
            salinity_stress=15.0,
            high_temp_stress=42.0,
            low_temp_stress=0.0,
            disease_environment_risk=30.0,
            energy_cost=10.0,
            confidence=0.7,
            requires_human_review=True,
        )

        self.assertEqual(score.score, 74.0)
        self.assertEqual(score.components["moisture_stress"], 80.0)

        with self.assertRaises(DecisionContractError):
            WorkNeedScore(
                action_type="irrigation",
                score=101.0,
                priority_rank=1,
            )

    def test_recommendation_is_always_decision_support_and_human_reviewed(self) -> None:
        recommendation = CoreRecommendation(
            action="ventilation",
            score=64.0,
            priority="medium",
            status="caution",
            reasons=("humidity is high",),
            expected_effects=("humidity may decrease",),
            risks=("outside air may be cold",),
            evidence_rule_ids=("rule.humidity.vpd",),
            prediction_refs=("prediction.humidity.3h",),
            simulation_refs=("scenario.ventilation",),
        )

        self.assertEqual(recommendation.mode, "decision_support")
        self.assertTrue(recommendation.requires_human_review)

        with self.assertRaises(DecisionContractError):
            CoreRecommendation(
                action="ventilation",
                score=-1.0,
                priority="medium",
                status="recommend",
                reasons=("humidity is high",),
            )

    def test_legacy_recommendation_result_exposes_decision_support_mode(self) -> None:
        recommendation = RecommendationResult(
            action_type="irrigation",
            priority="high",
            confidence=0.72,
            reason="substrate moisture is low",
            expected_effect="moisture stress may decrease",
            risks=("over-irrigation risk requires review",),
            evidence_references=(
                EvidenceReference(
                    source_type="manual_rule",
                    title="substrate moisture rule",
                    reference_id="rule.irrigation.moisture",
                ),
            ),
            safety_flags=("decision_support_only",),
            model_used="literature_manual_rules",
            fallback_used=True,
        )

        self.assertEqual(recommendation.mode, "decision_support")
        self.assertTrue(recommendation.requires_human_review)
        self.assertEqual(recommendation.action, "irrigation")


if __name__ == "__main__":
    unittest.main()
