import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from libsbapi.decision_contract import (
    GreenhouseSnapshot,
    PredictionResult,
    RootZoneState,
    SensorState,
)
from libsbapi.evidence_rules import load_evidence_rules
from libsbapi.scenario_simulator import (
    ScenarioCandidate,
    ScenarioSimulationResult,
    ScenarioSimulationRequest,
    simulate_scenarios,
)


class ScenarioSimulatorTest(unittest.TestCase):
    def test_compares_three_actions_plus_no_action_with_directional_outputs(self) -> None:
        request = ScenarioSimulationRequest(
            snapshot=_snapshot(),
            candidate_actions=(
                ScenarioCandidate("irrigation"),
                ScenarioCandidate("ventilation_dehumidification"),
                ScenarioCandidate("shading_high_temperature"),
                ScenarioCandidate("no_action"),
            ),
            evidence_rules=load_evidence_rules(),
        )

        report = simulate_scenarios(request)

        self.assertEqual(len(report.scenarios), 4)
        irrigation = _scenario(report.scenarios, "irrigation")
        no_action = _scenario(report.scenarios, "no_action")
        self.assertIn("moisture likely increases", irrigation.expected_state_direction)
        self.assertIn("humidity risk may increase", irrigation.potential_risks)
        self.assertIn("EC issue remains unresolved", no_action.expected_state_direction)
        self.assertIn("not a validated causal simulation", irrigation.not_validated_warning)

    def test_optional_prediction_is_reported_as_assumption_without_precise_numbers(self) -> None:
        request = ScenarioSimulationRequest(
            snapshot=_snapshot(),
            candidate_actions=(ScenarioCandidate("heating_low_temperature"),),
            evidence_rules=load_evidence_rules(),
            predictions=(
                PredictionResult(
                    target="temperature_c",
                    horizon_hours=3,
                    predicted_value=9.8,
                    predicted_delta=-1.2,
                    confidence=0.54,
                    model_used="gam_prototype",
                    metrics=(
                        ("training_rows", 180.0),
                        ("validation_mae", 0.2),
                        ("baseline_mae", 0.4),
                        ("validation_r2", 0.2),
                        ("missing_feature_ratio", 0.02),
                    ),
                ),
            ),
        )

        scenario = simulate_scenarios(request).scenarios[0]

        self.assertIn(
            "model prediction considered after confidence gate: temperature_c",
            scenario.assumptions,
        )
        self.assertIn("temperature likely increases", scenario.expected_state_direction)
        self.assertNotIn("9.8", " ".join(scenario.expected_state_direction))

    def test_weak_prediction_is_reported_as_rule_fallback_without_confidence_bonus(self) -> None:
        request = ScenarioSimulationRequest(
            snapshot=_snapshot(),
            candidate_actions=(ScenarioCandidate("irrigation"),),
            evidence_rules=load_evidence_rules(),
            predictions=(
                PredictionResult(
                    target="substrate_moisture_pct",
                    horizon_hours=3,
                    predicted_value=44.0,
                    predicted_delta=-4.0,
                    confidence=0.72,
                    model_used="gam_prototype",
                    metrics=(
                        ("training_rows", 45.0),
                        ("validation_mae", 0.71),
                        ("baseline_mae", 0.61),
                        ("validation_r2", -0.1),
                        ("missing_feature_ratio", 0.05),
                    ),
                ),
            ),
        )

        scenario = simulate_scenarios(request).scenarios[0]

        self.assertEqual(scenario.confidence, 0.56)
        self.assertIn(
            "model prediction fallback: usable training rows are below the configured minimum",
            scenario.assumptions,
        )
        self.assertNotIn("model prediction considered: substrate_moisture_pct", scenario.assumptions)

    def test_cli_runs_sample_input_and_writes_scenario_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "scenario_output.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_scenario_simulation.py",
                    "examples/sample_scenario_simulation_input.json",
                    str(output_path),
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("what-if scenario estimate", payload["summary"])
            self.assertEqual(len(payload["scenarios"]), 4)
            self.assertIn("not a validated causal simulation", completed.stdout)

    def test_sample_output_file_matches_current_cli_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "scenario_output.json"

            subprocess.run(
                [
                    sys.executable,
                    "scripts/run_scenario_simulation.py",
                    "examples/sample_scenario_simulation_input.json",
                    str(output_path),
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
                capture_output=True,
                text=True,
            )

            expected = json.loads(
                Path("examples/sample_scenario_simulation_output.json").read_text(
                    encoding="utf-8"
                )
            )
            actual = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(actual, expected)


def _snapshot() -> GreenhouseSnapshot:
    return GreenhouseSnapshot(
        timestamp="2026-06-25T09:00:00+09:00",
        sensor_state=SensorState(
            temperature_c=29.0,
            humidity_pct=88.0,
            vpd_kpa=1.35,
            radiation_w_m2=710.0,
        ),
        root_zone_state=RootZoneState(substrate_moisture_pct=49.0, root_zone_ec=2.5),
    )


def _scenario(
    scenarios: tuple[ScenarioSimulationResult, ...],
    action_type: str,
) -> ScenarioSimulationResult:
    matches = [item for item in scenarios if item.action_type == action_type]
    if len(matches) != 1:
        raise AssertionError(f"expected one scenario for {action_type}, got {len(matches)}")
    return matches[0]


if __name__ == "__main__":
    _ = unittest.main()
