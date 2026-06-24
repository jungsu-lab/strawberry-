import unittest

from libsbapi.greenhouse_models import (
    DiseaseControlWork,
    GreenhouseEnvironment,
    GreenhouseState,
    HarvestWork,
    IrrigationWork,
    LeafPruningWork,
)
from libsbapi.simulation_runner import (
    Scenario,
    ScheduledWork,
    compare_scenarios,
    simulate_scenario,
)


def baseline_state() -> GreenhouseState:
    return GreenhouseState(
        substrate_moisture_pct=56.0,
        drain_ec=1.8,
        disease_risk=0.42,
        ripe_fruit_ratio=0.62,
        fruit_count=95,
        leaf_density=0.78,
        ventilation_score=0.36,
        yield_potential=1.0,
        marketable_yield_kg=0.0,
        quality_risk=0.14,
        coloring_pct=82.0,
    )


def humid_environment() -> GreenhouseEnvironment:
    return GreenhouseEnvironment(
        solar_radiation_w_m2=520.0,
        vpd_kpa=0.38,
        humidity_pct=89.0,
        rain_probability=55.0,
        inside_temperature_c=25.0,
        leaf_wetness_hours=5.0,
    )


class SimulationRunnerTest(unittest.TestCase):
    def test_simulate_scenario_applies_daily_work_and_weather_drift(self):
        scenario = Scenario(
            name="irrigation and pruning",
            initial_state=baseline_state(),
            environment=humid_environment(),
            days=3,
            schedule=(
                ScheduledWork(day=1, work=IrrigationWork(volume_l=1.2)),
                ScheduledWork(day=2, work=LeafPruningWork(removal_ratio=0.18)),
            ),
        )

        records = simulate_scenario(scenario)

        self.assertEqual([record.day for record in records], [0, 1, 2, 3])
        self.assertEqual(records[0].scenario, "irrigation and pruning")
        self.assertGreater(records[1].substrate_moisture_pct, records[0].substrate_moisture_pct)
        self.assertLess(records[2].leaf_density, records[1].leaf_density)
        self.assertGreater(records[3].disease_risk, records[2].disease_risk)
        self.assertIn("ambient humid/rainy pressure increased disease risk", records[3].notes)

    def test_compare_scenarios_returns_combined_timeline_and_end_state_summary(self):
        baseline = baseline_state()
        environment = humid_environment()
        scenarios = (
            Scenario(
                name="harvest now",
                initial_state=baseline,
                environment=environment,
                days=2,
                schedule=(ScheduledWork(day=1, work=HarvestWork(pick_ratio=0.45)),),
            ),
            Scenario(
                name="spray and prune",
                initial_state=baseline,
                environment=environment,
                days=2,
                schedule=(
                    ScheduledWork(day=1, work=DiseaseControlWork(effectiveness=0.55)),
                    ScheduledWork(day=1, work=LeafPruningWork(removal_ratio=0.12)),
                ),
            ),
        )

        result = compare_scenarios(scenarios)

        self.assertEqual(len(result.timeline), 6)
        self.assertEqual([summary.scenario for summary in result.end_states], ["harvest now", "spray and prune"])
        harvest_summary = result.end_states[0]
        control_summary = result.end_states[1]
        self.assertGreater(harvest_summary.marketable_yield_kg, control_summary.marketable_yield_kg)
        self.assertLess(control_summary.disease_risk, harvest_summary.disease_risk)
        self.assertTrue(result.evidence_log)


if __name__ == "__main__":
    _ = unittest.main()
