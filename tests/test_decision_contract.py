import unittest
from pathlib import Path

from libsbapi.decision_contract import (
    ActionCandidate,
    DecisionContractError,
    EvidenceReference,
    GreenhouseSnapshot,
    PredictionResult,
    RecommendationResult,
    RootZoneState,
    SensorState,
    WorkHistoryEvent,
)
from libsbapi.decision_contract_io import load_decision_contract_sample


class DecisionContractTest(unittest.TestCase):
    def test_greenhouse_snapshot_exposes_required_state_fields(self) -> None:
        snapshot = GreenhouseSnapshot(
            timestamp="2025-06-20T09:00:00+09:00",
            sensor_state=SensorState(
                temperature_c=27.4,
                humidity_pct=88.0,
                vpd_kpa=0.49,
                radiation_w_m2=520.0,
                co2_ppm=610.0,
            ),
            root_zone_state=RootZoneState(
                substrate_moisture_pct=58.0,
                root_zone_ec=1.4,
                root_zone_ph=6.1,
            ),
            recent_work_history=(
                WorkHistoryEvent(
                    timestamp="2025-06-20T06:30:00+09:00",
                    action_type="irrigation",
                    source="farm_work_log",
                ),
            ),
        )

        self.assertEqual(snapshot.temperature_c, 27.4)
        self.assertEqual(snapshot.humidity_pct, 88.0)
        self.assertEqual(snapshot.substrate_moisture_pct, 58.0)
        self.assertEqual(snapshot.root_zone_ec, 1.4)
        self.assertEqual(snapshot.recent_work_history[0].action_type, "irrigation")

    def test_recommendation_result_preserves_decision_support_metadata(self) -> None:
        recommendation = RecommendationResult(
            action_type="ventilation",
            priority="medium",
            confidence=0.62,
            reason="humidity remains high",
            expected_effect="lower humidity and reduce canopy wetness risk",
            risks=("rapid ventilation can cool the greenhouse",),
            evidence_references=(
                EvidenceReference(
                    source_type="manual_rule",
                    title="humidity threshold",
                    reference_id="manual.humidity",
                ),
            ),
            safety_flags=("decision_support_only", "requires_human_review"),
            model_used="rule_based",
            fallback_used=True,
            action_candidate=ActionCandidate(
                action_type="ventilation",
                target_window="today_morning",
                rationale="humidity remains high",
            ),
            prediction=PredictionResult(
                target="humidity_pct",
                horizon_hours=3,
                predicted_value=90.0,
                predicted_delta=2.0,
                confidence=0.54,
                model_used="gam_prototype",
            ),
        )

        self.assertEqual(recommendation.action_type, "ventilation")
        self.assertIn("decision_support_only", recommendation.safety_flags)
        self.assertEqual(recommendation.prediction.horizon_hours, 3)
        self.assertTrue(recommendation.fallback_used)

    def test_invalid_ranges_are_rejected(self) -> None:
        with self.assertRaises(DecisionContractError):
            SensorState(humidity_pct=140.0)

        with self.assertRaises(DecisionContractError):
            RecommendationResult(
                action_type="irrigation",
                priority="urgent",
                confidence=0.5,
                reason="root zone is dry",
                expected_effect="increase substrate moisture",
                risks=(),
                evidence_references=(),
                safety_flags=("decision_support_only",),
                model_used="rule_based",
                fallback_used=False,
            )

    def test_sample_decision_contract_json_loads(self) -> None:
        sample_path = Path("examples/sample_decision_contract.json")

        sample = load_decision_contract_sample(sample_path)

        self.assertEqual(sample.snapshot.timestamp, "2025-06-20T09:00:00+09:00")
        self.assertEqual(sample.snapshot.growth_stage, "harvest")
        self.assertEqual(sample.action_candidates[0].action_type, "ventilation")
        self.assertEqual(sample.predictions[0].target, "humidity_pct")
        self.assertIn("requires_human_review", sample.recommendation.safety_flags)


if __name__ == "__main__":
    unittest.main()
