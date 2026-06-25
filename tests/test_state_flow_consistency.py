import subprocess
import sys
import unittest

from dashboard.greenhouse_dashboard import _current_state_rows
from libsbapi.current_state_builder import CurrentStateBuilder
from libsbapi.decision_contract import CurrentGreenhouseState
from libsbapi.evidence_rules import load_evidence_rules
from libsbapi.offline_demo import _greenhouse_state_from_current, _scenario_inputs_from_current, build_demo_from_current_state
from libsbapi.work_need_scorer import WorkNeedScorer


class StateFlowConsistencyTest(unittest.TestCase):
    def test_root_zone_moisture_is_preserved_through_normalized_and_scenario_input(self) -> None:
        payload = {"snapshot": {"root_zone_moisture_pct": 59.0, "inside_temperature_c": 24.0, "inside_humidity_pct": 80.0}}

        state = CurrentStateBuilder().from_daily_context(payload, source_label="unit_test")
        scenario_state = _greenhouse_state_from_current(state)

        self.assertEqual(state.root_zone_moisture, 59.0)
        self.assertEqual(scenario_state.substrate_moisture_pct, 59.0)

    def test_missing_substrate_moisture_proxy_is_warned_when_root_zone_is_used(self) -> None:
        payload = {"snapshot": {"root_zone_moisture_pct": 59.0}}

        state = CurrentStateBuilder().from_daily_context(payload, source_label="unit_test")

        self.assertEqual(state.substrate_moisture, 59.0)
        self.assertIn("substrate_moisture missing, using root_zone_moisture as proxy", state.quality_warnings)

    def test_different_substrate_and_root_zone_moisture_are_kept_separate(self) -> None:
        payload = {"snapshot": {"substrate_moisture_pct": 61.0, "root_zone_moisture_pct": 59.0}}

        state = CurrentStateBuilder().from_daily_context(payload, source_label="unit_test")

        self.assertEqual(state.substrate_moisture, 61.0)
        self.assertEqual(state.root_zone_moisture, 59.0)

    def test_scenario_adapter_preserves_zero_values_instead_of_defaulting(self) -> None:
        state = CurrentGreenhouseState(root_zone_moisture=0.0, drain_ec=0.0)

        scenario_state = _greenhouse_state_from_current(state)

        self.assertEqual(scenario_state.substrate_moisture_pct, 0.0)
        self.assertEqual(scenario_state.drain_ec, 0.0)

    def test_scorer_uses_normalized_root_zone_moisture(self) -> None:
        state = CurrentGreenhouseState(root_zone_moisture=59.0, vpd=0.8, solar_radiation=300.0)

        irrigation = _score(WorkNeedScorer(load_evidence_rules()).score(state), "irrigation")

        self.assertLess(irrigation.score, 70.0)
        self.assertIn(irrigation.status, {"hold", "monitor", "caution"})

    def test_current_state_dashboard_rows_are_labeled_as_current_state_not_scenario_state(self) -> None:
        rows = _current_state_rows(CurrentGreenhouseState(root_zone_moisture=59.0, substrate_moisture=61.0))
        by_label = {row["항목"]: row["값"] for row in rows}

        self.assertEqual(by_label["배지수분"], "61.00")
        self.assertEqual(by_label["근권수분"], "59.00")

    def test_missing_ec_fields_reduce_ec_score_confidence(self) -> None:
        scorer = WorkNeedScorer(load_evidence_rules())
        full_ec_state = CurrentGreenhouseState(feed_ec=1.2, drain_ec=1.4, root_ec=1.5)
        partial_ec_state = CurrentGreenhouseState(drain_ec=1.4)

        full = _score(scorer.score(full_ec_state), "nutrient_ec_check")
        partial = _score(scorer.score(partial_ec_state), "nutrient_ec_check")

        self.assertLess(partial.confidence, full.confidence)
        self.assertTrue(partial.requires_human_review)

    def test_confidence_uses_sensor_coverage_for_each_action(self) -> None:
        scorer = WorkNeedScorer(load_evidence_rules())
        complete = CurrentGreenhouseState(air_temp=29.0, humidity=91.0, vpd=0.32, solar_radiation=720.0)
        incomplete = CurrentGreenhouseState(air_temp=29.0)

        full_shading = _score(scorer.score(complete), "shading_high_temperature")
        partial_shading = _score(scorer.score(incomplete), "shading_high_temperature")
        full_ventilation = _score(scorer.score(complete), "ventilation_dehumidification")
        partial_ventilation = _score(scorer.score(incomplete), "ventilation_dehumidification")

        self.assertGreaterEqual(full_shading.confidence, 0.65)
        self.assertLess(partial_shading.confidence, full_shading.confidence)
        self.assertLess(partial_ventilation.confidence, full_ventilation.confidence)

    def test_missing_vpd_is_calculated_or_warned(self) -> None:
        state = CurrentStateBuilder().from_daily_context(
            {"snapshot": {"inside_temperature_c": 25.0, "inside_humidity_pct": 80.0}},
            source_label="unit_test",
        )

        self.assertIsNotNone(state.vpd)
        self.assertIn("vpd calculated from air temperature and humidity", state.quality_warnings)

    def test_audit_state_flow_script_runs_offline(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/audit_state_flow.py"],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("variable | raw_input | current_state", result.stdout)
        self.assertIn("root_zone_moisture", result.stdout)
        self.assertIn("scenario_input", result.stdout)

    def test_build_demo_from_current_state_uses_supplied_dashboard_state(self) -> None:
        state = CurrentGreenhouseState(
            air_temp=24.0,
            humidity=70.0,
            vpd=0.8,
            solar_radiation=300.0,
            root_zone_moisture=59.0,
            drain_ec=1.4,
        )

        demo = build_demo_from_current_state(state)
        irrigation = _score(demo.work_scores, "irrigation")

        self.assertEqual(demo.current_state.root_zone_moisture, 59.0)
        self.assertLess(irrigation.score, 70.0)

    def test_scenario_inputs_use_context_proxy_values_and_report_remaining_placeholders(self) -> None:
        state = CurrentGreenhouseState(
            air_temp=24.0,
            humidity=70.0,
            vpd=0.8,
            solar_radiation=300.0,
            root_zone_moisture=59.0,
            drain_ec=1.4,
        )
        payload = {
            "snapshot": {
                "vent_open_pct": 12.0,
                "weather": {"rain_probability": 44.0},
                "image": {
                    "disease_spot_ratio": 0.07,
                    "ripe_fruit_ratio": 0.42,
                    "fruit_count": 32,
                    "leaf_density": 0.81,
                },
            }
        }

        scenario_state, scenario_environment, warnings = _scenario_inputs_from_current(state, payload)

        self.assertEqual(scenario_state.disease_risk, 0.07)
        self.assertEqual(scenario_state.ripe_fruit_ratio, 0.42)
        self.assertEqual(scenario_state.fruit_count, 32)
        self.assertEqual(scenario_state.leaf_density, 0.81)
        self.assertEqual(scenario_state.ventilation_score, 0.12)
        self.assertEqual(scenario_environment.rain_probability, 44.0)
        self.assertTrue(any("prototype placeholder" in warning for warning in warnings))


def _score(scores: tuple, action_type: str):
    matches = [item for item in scores if item.action_type == action_type]
    if len(matches) != 1:
        raise AssertionError(f"expected one score for {action_type}, got {len(matches)}")
    return matches[0]


if __name__ == "__main__":
    unittest.main()
