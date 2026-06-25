import unittest
from pathlib import Path

from libsbapi.action_recommenders import ActionRecommendationEngine
from libsbapi.decision_contract import RecommendationResult
from libsbapi.decision_contract_io import load_decision_contract_sample
from libsbapi.evidence_rules import load_evidence_rules
from libsbapi.scenario_simulator import (
    NOT_VALIDATED_WARNING,
    ScenarioCandidate,
    ScenarioSimulationReport,
    ScenarioSimulationResult,
    ScenarioSimulationRequest,
    simulate_scenarios,
)


class PostStep6IntegrationTest(unittest.TestCase):
    def test_decision_support_pipeline_runs_end_to_end_with_action_specific_prediction_use(self) -> None:
        sample = load_decision_contract_sample(Path("examples/sample_decision_contract.json"))
        evidence_rules = load_evidence_rules()
        prediction = sample.predictions[0]

        engine = ActionRecommendationEngine(evidence_rules)
        recommendations = engine.recommend(
            sample.snapshot,
            prediction=prediction,
        )
        auxiliary_alerts = engine.auxiliary_alerts(sample.snapshot, prediction=prediction)
        scenario_report = simulate_scenarios(
            ScenarioSimulationRequest(
                snapshot=sample.snapshot,
                candidate_actions=(
                    ScenarioCandidate("irrigation"),
                    ScenarioCandidate("ventilation_dehumidification"),
                    ScenarioCandidate("nutrient_ec_check"),
                    ScenarioCandidate("no_action"),
                ),
                evidence_rules=evidence_rules,
                predictions=(prediction,),
            )
        )

        self.assertEqual(
            {item.action_type for item in recommendations},
            {
                "irrigation",
                "nutrient_ec_check",
                "ventilation_dehumidification",
                "shading_high_temperature",
                "heating_low_temperature",
            },
        )
        self.assertFalse(any(item.action_type == "disease_environment_risk_proxy" for item in recommendations))
        self.assertTrue(any(item.action_type == "disease_environment_risk_proxy" for item in auxiliary_alerts))
        self.assertTrue(all(_has_required_recommendation_fields(item) for item in recommendations))
        self.assertTrue(all(_has_required_recommendation_fields(item) for item in auxiliary_alerts))
        model_actions = {
            item.action_type
            for item in (*recommendations, *auxiliary_alerts)
            if item.model_used == "rule_adjusted_gam_prototype"
        }
        self.assertEqual(
            model_actions,
            {
                "ventilation_dehumidification",
                "disease_environment_risk_proxy",
                "leaf_removal_caution",
            },
        )
        self.assertTrue(
            all(
                item.fallback_used
                for item in (*recommendations, *auxiliary_alerts)
                if item.action_type not in model_actions
            )
        )
        self.assertEqual(len(scenario_report.scenarios), 4)
        self.assertIn("what-if scenario estimate", scenario_report.summary)
        ventilation = _scenario(scenario_report, "ventilation_dehumidification")
        irrigation = _scenario(scenario_report, "irrigation")
        self.assertIn(
            "model prediction considered after confidence gate: humidity_pct",
            ventilation.assumptions,
        )
        self.assertNotIn("humidity_pct", " ".join(irrigation.assumptions))
        self.assertTrue(
            all(item.not_validated_warning == NOT_VALIDATED_WARNING for item in scenario_report.scenarios)
        )


def _has_required_recommendation_fields(item: RecommendationResult) -> bool:
    return (
        bool(item.reason)
        and bool(item.risks)
        and bool(item.evidence_references)
        and 0.0 <= item.confidence <= 1.0
        and bool(item.safety_flags)
    )


def _scenario(
    report: ScenarioSimulationReport,
    action_type: str,
) -> ScenarioSimulationResult:
    matches = [item for item in report.scenarios if item.action_type == action_type]
    if len(matches) != 1:
        raise AssertionError(f"expected one scenario for {action_type}, got {len(matches)}")
    return matches[0]


if __name__ == "__main__":
    _ = unittest.main()
