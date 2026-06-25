import unittest

from libsbapi.greenhouse_models import GreenhouseEnvironment, GreenhouseState
from libsbapi.scenario_comparison import compare_action_candidates


class ShortHorizonScenarioComparisonTest(unittest.TestCase):
    def test_irrigation_candidate_marks_moisture_improvement(self) -> None:
        result = _candidate("irrigation")

        self.assertGreater(result.moisture_delta, 0.0)
        self.assertIn("moisture", " ".join(result.expected_benefits))
        self.assertFalse(result.is_training_label)

    def test_ventilation_candidate_reduces_humidity_or_disease_environment_risk(self) -> None:
        result = _candidate("ventilation")

        self.assertLess(result.humidity_delta, 0.0)
        self.assertLess(result.disease_environment_risk_delta, 0.0)
        self.assertIn("heuristic", result.model_status)

    def test_shading_candidate_reduces_high_temperature_or_radiation_stress(self) -> None:
        result = _candidate("shading")

        self.assertLess(result.temperature_delta, 0.0)
        self.assertLess(result.vpd_delta, 0.0)
        self.assertIn("heat", " ".join(result.expected_benefits))

    def test_heat_preservation_improves_low_temperature_risk_but_increases_energy(self) -> None:
        result = _candidate("heat_preservation_heating_review")

        self.assertGreater(result.temperature_delta, 0.0)
        self.assertGreater(result.energy_cost_delta, 0.0)
        self.assertIn("energy", " ".join(result.risks))

    def test_comparison_includes_required_candidates_and_no_training_label_language(self) -> None:
        report = compare_action_candidates(_state(), _environment(), horizon_hours=3)
        actions = {item.action_type for item in report.scenarios}

        self.assertEqual(
            actions,
            {
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
            },
        )
        self.assertIn("휴리스틱 의사결정 보조", report.not_training_label_notice)
        self.assertIn("fake supervised", report.not_training_label_notice)
        self.assertTrue(all(not item.is_training_label for item in report.scenarios))


def _candidate(action_type: str):
    report = compare_action_candidates(_state(), _environment(), horizon_hours=3, candidates=(action_type,))
    return report.scenarios[0]


def _state() -> GreenhouseState:
    return GreenhouseState(
        substrate_moisture_pct=43.0,
        drain_ec=2.4,
        disease_risk=0.62,
        ripe_fruit_ratio=0.4,
        fruit_count=80,
        leaf_density=0.82,
        ventilation_score=0.25,
        yield_potential=1.0,
        marketable_yield_kg=0.0,
        quality_risk=0.12,
        feed_ec=1.4,
    )


def _environment() -> GreenhouseEnvironment:
    return GreenhouseEnvironment(
        solar_radiation_w_m2=720.0,
        vpd_kpa=1.35,
        humidity_pct=91.0,
        rain_probability=65.0,
        inside_temperature_c=29.0,
        leaf_wetness_hours=6.0,
    )


if __name__ == "__main__":
    unittest.main()
