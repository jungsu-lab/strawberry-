import unittest

from libsbapi.action_recommenders import ActionRecommendationEngine
from libsbapi.decision_contract import (
    EvidenceReference,
    GreenhouseSnapshot,
    PredictionResult,
    RecommendationResult,
    RootZoneState,
    SensorState,
)
from libsbapi.evidence_rules import load_evidence_rules
from libsbapi.prediction_confidence import (
    INSUFFICIENT_DATA_FALLBACK,
    MISSING_TARGET_FALLBACK,
    USABLE_MODEL,
    WEAK_MODEL_FALLBACK,
    PredictionGateConfig,
    PredictionGateInput,
    apply_prediction_gate_to_recommendation,
    evaluate_prediction_gate,
    gate_recommendation_prediction,
)


class PredictionConfidenceTest(unittest.TestCase):
    def test_gam_better_than_baseline_is_usable(self) -> None:
        recommendation = _recommendation(
            prediction=_prediction(
                metrics=(
                    ("training_rows", 220.0),
                    ("validation_mae", 0.42),
                    ("baseline_mae", 0.61),
                    ("validation_r2", 0.18),
                    ("missing_feature_ratio", 0.04),
                )
            )
        )

        gated = gate_recommendation_prediction(
            recommendation,
            PredictionGateConfig(min_usable_rows=100),
        )

        self.assertFalse(gated.fallback_used)
        self.assertEqual(gated.model_used, "gam_prototype")
        self.assertEqual(gated.confidence, 0.72)
        self.assertIn(USABLE_MODEL, gated.safety_flags)

    def test_gam_worse_than_baseline_falls_back_to_rules(self) -> None:
        decision = evaluate_prediction_gate(
            PredictionGateInput(
                target="substrate_moisture_pct",
                usable_training_rows=240,
                target_available=True,
                validation_mae=0.71,
                baseline_mae=0.61,
                validation_r2=0.08,
                missing_feature_ratio=0.05,
                model_used="gam_prototype",
                model_confidence=0.74,
            )
        )
        gated = apply_prediction_gate_to_recommendation(_recommendation(), decision)

        self.assertEqual(decision.status, WEAK_MODEL_FALLBACK)
        self.assertTrue(gated.fallback_used)
        self.assertEqual(gated.model_used, "literature_manual_rules")
        self.assertLess(gated.confidence, 0.5)
        self.assertIn("model_not_better_than_baseline", gated.safety_flags)
        self.assertIn("rule_based_fallback", gated.safety_flags)

    def test_insufficient_rows_skip_model_use(self) -> None:
        decision = evaluate_prediction_gate(
            PredictionGateInput(
                target="humidity_pct",
                usable_training_rows=45,
                target_available=True,
                validation_mae=0.2,
                baseline_mae=0.4,
                validation_r2=0.2,
                missing_feature_ratio=0.02,
                model_used="gam_prototype",
                model_confidence=0.7,
            ),
            PredictionGateConfig(min_usable_rows=100),
        )

        self.assertEqual(decision.status, INSUFFICIENT_DATA_FALLBACK)
        self.assertFalse(decision.use_model)
        self.assertTrue(decision.fallback_used)
        self.assertIn("insufficient_training_rows", decision.safety_flags)

    def test_missing_target_skips_model_use(self) -> None:
        decision = evaluate_prediction_gate(
            PredictionGateInput(
                target=None,
                usable_training_rows=240,
                target_available=False,
                validation_mae=0.2,
                baseline_mae=0.4,
                validation_r2=0.2,
                missing_feature_ratio=0.02,
                model_used="gam_prototype",
                model_confidence=0.7,
            )
        )

        self.assertEqual(decision.status, MISSING_TARGET_FALLBACK)
        self.assertFalse(decision.use_model)
        self.assertIn("missing_target", decision.safety_flags)

    def test_negative_r2_is_weak_model_fallback(self) -> None:
        decision = evaluate_prediction_gate(
            PredictionGateInput(
                target="humidity_pct",
                usable_training_rows=180,
                target_available=True,
                validation_mae=0.2,
                baseline_mae=0.4,
                validation_r2=-0.01,
                missing_feature_ratio=0.02,
                model_used="gam_prototype",
                model_confidence=0.7,
            )
        )

        self.assertEqual(decision.status, WEAK_MODEL_FALLBACK)
        self.assertIn("low_validation_r2", decision.safety_flags)

    def test_unrelated_usable_prediction_does_not_mark_all_actions_model_driven(self) -> None:
        snapshot = GreenhouseSnapshot(
            timestamp="2026-06-25T09:00:00+09:00",
            sensor_state=SensorState(temperature_c=29.0, humidity_pct=91.0, vpd_kpa=0.22),
            root_zone_state=RootZoneState(substrate_moisture_pct=48.0, root_zone_ec=2.7),
        )

        recommendations = ActionRecommendationEngine(load_evidence_rules()).recommend(
            snapshot,
            prediction=_prediction(),
        )

        irrigation = _single(recommendations, "irrigation")
        ventilation = _single(recommendations, "ventilation_dehumidification")
        ec_check = _single(recommendations, "nutrient_ec_check")
        self.assertEqual(irrigation.model_used, "gam_prototype")
        self.assertFalse(irrigation.fallback_used)
        self.assertEqual(ventilation.model_used, "literature_manual_rules")
        self.assertTrue(ventilation.fallback_used)
        self.assertNotIn(USABLE_MODEL, ventilation.safety_flags)
        self.assertEqual(ec_check.model_used, "literature_manual_rules")
        self.assertTrue(ec_check.fallback_used)

    def test_multiple_predictions_are_matched_to_each_action_type(self) -> None:
        snapshot = GreenhouseSnapshot(
            timestamp="2026-06-25T09:00:00+09:00",
            sensor_state=SensorState(temperature_c=22.0, humidity_pct=80.0, vpd_kpa=0.5),
            root_zone_state=RootZoneState(substrate_moisture_pct=65.0),
        )

        recommendations = ActionRecommendationEngine(load_evidence_rules()).recommend(
            snapshot,
            prediction=(
                _prediction(predicted_value=40.0, predicted_delta=-25.0),
                _prediction(
                    target="humidity_pct",
                    predicted_value=91.0,
                    predicted_delta=3.0,
                    model_used="gam_humidity",
                ),
            ),
        )

        irrigation = _single(recommendations, "irrigation")
        ventilation = _single(recommendations, "ventilation_dehumidification")
        self.assertEqual(irrigation.model_used, "gam_prototype")
        self.assertFalse(irrigation.fallback_used)
        self.assertIn("predicted substrate moisture", irrigation.reason)
        self.assertIn(irrigation.priority, {"medium", "high"})
        self.assertEqual(ventilation.model_used, "gam_humidity")
        self.assertFalse(ventilation.fallback_used)
        self.assertIn("predicted humidity", ventilation.reason)

    def test_weak_prediction_does_not_change_recommendation_priority(self) -> None:
        snapshot = GreenhouseSnapshot(
            timestamp="2026-06-25T09:00:00+09:00",
            sensor_state=SensorState(temperature_c=22.0, humidity_pct=60.0, vpd_kpa=0.7),
            root_zone_state=RootZoneState(substrate_moisture_pct=65.0),
        )

        recommendations = ActionRecommendationEngine(load_evidence_rules()).recommend(
            snapshot,
            prediction=_prediction(
                predicted_value=40.0,
                predicted_delta=-25.0,
                metrics=(
                    ("training_rows", 45.0),
                    ("validation_mae", 0.71),
                    ("baseline_mae", 0.61),
                    ("validation_r2", -0.1),
                    ("missing_feature_ratio", 0.05),
                ),
            ),
        )

        irrigation = _single(recommendations, "irrigation")
        self.assertEqual(irrigation.priority, "low")
        self.assertNotIn("predicted substrate moisture", irrigation.reason)
        self.assertTrue(irrigation.fallback_used)


def _prediction(
    target: str = "substrate_moisture_pct",
    predicted_value: float = 53.0,
    predicted_delta: float = -4.0,
    model_used: str = "gam_prototype",
    metrics: tuple[tuple[str, float], ...] = (
        ("training_rows", 220.0),
        ("validation_mae", 0.42),
        ("baseline_mae", 0.61),
        ("validation_r2", 0.18),
        ("missing_feature_ratio", 0.04),
    ),
) -> PredictionResult:
    return PredictionResult(
        target=target,
        horizon_hours=3,
        predicted_value=predicted_value,
        predicted_delta=predicted_delta,
        confidence=0.72,
        model_used=model_used,
        metrics=metrics,
    )


def _recommendation(
    prediction: PredictionResult | None = None,
) -> RecommendationResult:
    return RecommendationResult(
        action_type="irrigation",
        priority="medium",
        confidence=0.76,
        reason="predicted substrate moisture is near the lower rule boundary",
        expected_effect="maintain root-zone moisture in the target range",
        risks=("manual review required before changing irrigation volume",),
        evidence_references=(
            EvidenceReference(
                source_type="manual_rule",
                title="strawberry irrigation threshold",
                reference_id="manual.irrigation.moisture",
            ),
        ),
        safety_flags=("decision_support_only",),
        model_used="gam_prototype",
        fallback_used=False,
        prediction=prediction or _prediction(),
    )


def _single(
    recommendations: tuple[RecommendationResult, ...],
    action_type: str,
) -> RecommendationResult:
    matches = [item for item in recommendations if item.action_type == action_type]
    if len(matches) != 1:
        raise AssertionError(f"expected one {action_type} recommendation, got {len(matches)}")
    return matches[0]


if __name__ == "__main__":
    unittest.main()
