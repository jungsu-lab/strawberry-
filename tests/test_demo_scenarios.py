import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_demo_scenarios import (
    DEFAULT_SCENARIO_DIR,
    run_demo_scenarios,
)


EXPECTED_ACTIONS = {
    "01_irrigation_high_vpd_low_moisture.json": "irrigation",
    "02_ventilation_high_humidity_low_vpd.json": "ventilation_dehumidification",
    "03_nutrient_high_ec.json": "nutrient_ec_check",
    "04_heating_low_night_temperature.json": "heating_low_temperature",
}
EXPECTED_AUXILIARY_ALERTS = {
    "05_leaf_removal_caution.json": "leaf_removal_caution",
}


class DemoScenariosTest(unittest.TestCase):
    def test_demo_scenario_fixtures_exist_with_markdown_expectations(self) -> None:
        for json_name in (*EXPECTED_ACTIONS, *EXPECTED_AUXILIARY_ALERTS):
            scenario_path = DEFAULT_SCENARIO_DIR / json_name
            expected_path = scenario_path.with_suffix(".md")

            self.assertTrue(scenario_path.exists(), scenario_path)
            self.assertTrue(expected_path.exists(), expected_path)
            self.assertIn("Expected behavior", expected_path.read_text(encoding="utf-8"))

    def test_each_demo_scenario_produces_reasonable_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            result = run_demo_scenarios(DEFAULT_SCENARIO_DIR, output_dir)

            self.assertEqual(len(result.scenario_reports), 5)
            for report in result.scenario_reports:
                expected_action = EXPECTED_ACTIONS.get(report.input_path.name)
                expected_alert = EXPECTED_AUXILIARY_ALERTS.get(report.input_path.name)
                recommendation_actions = [item.action_type for item in report.recommendations]
                auxiliary_actions = [item.action_type for item in report.auxiliary_alerts]
                if expected_action is not None:
                    self.assertIn(expected_action, recommendation_actions, report.input_path.name)
                if expected_alert is not None:
                    self.assertIn(expected_alert, auxiliary_actions, report.input_path.name)
                    self.assertNotIn(expected_alert, recommendation_actions, report.input_path.name)
                self.assertTrue(
                    set(recommendation_actions)
                    <= {
                        "irrigation",
                        "nutrient_ec_check",
                        "ventilation_dehumidification",
                        "shading_high_temperature",
                        "heating_low_temperature",
                    }
                )
                self.assertTrue(report.scenario_simulation.scenarios)
                self.assertTrue(
                    all(item.assumptions for item in report.scenario_simulation.scenarios)
                )
                self.assertIn("not a validated causal simulation", report.scenario_simulation.not_validated_warning)

    def test_demo_runner_writes_json_and_markdown_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            run_demo_scenarios(DEFAULT_SCENARIO_DIR, output_dir)
            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            markdown = (output_dir / "demo_report.md").read_text(encoding="utf-8")

            self.assertEqual(len(summary["scenarios"]), 5)
            self.assertIn("Irrigation check", markdown)
            self.assertIn("Focus recommendation:", markdown)
            self.assertIn("Auxiliary alerts:", markdown)
            self.assertIn("- Full ranking highlights:", markdown)
            self.assertIn("Rule-based assumptions", markdown)
            self.assertIn("not a validated causal simulation", markdown)


if __name__ == "__main__":
    _ = unittest.main()
