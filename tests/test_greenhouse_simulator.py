import unittest

from libsbapi.greenhouse_simulator import (
    DiseaseControlWork,
    GreenhouseEnvironment,
    GreenhouseSimulator,
    GreenhouseState,
    HarvestWork,
    IrrigationWork,
    LeafPruningWork,
)


class GreenhouseSimulatorTest(unittest.TestCase):
    def test_irrigation_increases_moisture_dilutes_ec_and_tracks_weather_drydown(self):
        state = GreenhouseState(
            substrate_moisture_pct=42.0,
            drain_ec=2.4,
            disease_risk=0.35,
            ripe_fruit_ratio=0.55,
            fruit_count=80,
            leaf_density=0.72,
            ventilation_score=0.45,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.1,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=720.0,
            vpd_kpa=1.45,
            humidity_pct=68.0,
            rain_probability=10.0,
            inside_temperature_c=27.0,
        )

        step = GreenhouseSimulator().apply(state, environment, IrrigationWork(volume_l=2.0))

        self.assertGreater(step.state.substrate_moisture_pct, state.substrate_moisture_pct)
        self.assertLess(step.state.drain_ec, state.drain_ec)
        self.assertIn("high solar/VPD accelerated moisture loss", step.notes)

    def test_irrigation_raises_disease_risk_when_substrate_becomes_overwet(self):
        state = GreenhouseState(
            substrate_moisture_pct=78.0,
            drain_ec=1.6,
            disease_risk=0.4,
            ripe_fruit_ratio=0.2,
            fruit_count=30,
            leaf_density=0.8,
            ventilation_score=0.35,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.2,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=180.0,
            vpd_kpa=0.28,
            humidity_pct=92.0,
            rain_probability=70.0,
            inside_temperature_c=23.0,
        )

        step = GreenhouseSimulator().apply(state, environment, IrrigationWork(volume_l=1.5))

        self.assertGreater(step.state.disease_risk, state.disease_risk)
        self.assertIn("over-wet substrate increased disease risk", step.notes)

    def test_negative_irrigation_volume_is_treated_as_no_irrigation(self):
        state = GreenhouseState(
            substrate_moisture_pct=54.0,
            drain_ec=1.9,
            disease_risk=0.3,
            ripe_fruit_ratio=0.25,
            fruit_count=40,
            leaf_density=0.6,
            ventilation_score=0.5,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.1,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=240.0,
            vpd_kpa=0.7,
            humidity_pct=72.0,
            rain_probability=10.0,
            inside_temperature_c=24.0,
        )

        step = GreenhouseSimulator().apply(state, environment, IrrigationWork(volume_l=-1.5))

        self.assertEqual(step.state.substrate_moisture_pct, state.substrate_moisture_pct)
        self.assertEqual(step.state.drain_ec, state.drain_ec)
        self.assertIn("irrigation skipped because volume was non-positive", step.notes)

    def test_disease_control_reduces_risk_but_bad_weather_adds_pressure_back(self):
        state = GreenhouseState(
            substrate_moisture_pct=66.0,
            drain_ec=1.8,
            disease_risk=0.82,
            ripe_fruit_ratio=0.35,
            fruit_count=70,
            leaf_density=0.84,
            ventilation_score=0.3,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.2,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=120.0,
            vpd_kpa=0.22,
            humidity_pct=94.0,
            rain_probability=85.0,
            inside_temperature_c=22.0,
        )

        step = GreenhouseSimulator().apply(state, environment, DiseaseControlWork(effectiveness=0.55))

        self.assertLess(step.state.disease_risk, state.disease_risk)
        self.assertGreater(step.state.disease_risk, 0.27)
        self.assertIn("humid/rainy conditions rebuilt disease pressure", step.notes)

    def test_harvest_removes_ripe_fruit_and_adds_marketable_yield(self):
        state = GreenhouseState(
            substrate_moisture_pct=58.0,
            drain_ec=1.7,
            disease_risk=0.3,
            ripe_fruit_ratio=0.82,
            fruit_count=120,
            leaf_density=0.7,
            ventilation_score=0.55,
            yield_potential=0.95,
            marketable_yield_kg=1.0,
            quality_risk=0.1,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=500.0,
            vpd_kpa=1.1,
            humidity_pct=74.0,
            rain_probability=20.0,
            inside_temperature_c=25.0,
        )

        step = GreenhouseSimulator().apply(state, environment, HarvestWork(pick_ratio=0.5))

        self.assertLess(step.state.ripe_fruit_ratio, state.ripe_fruit_ratio)
        self.assertLess(step.state.fruit_count, state.fruit_count)
        self.assertGreater(step.state.marketable_yield_kg, state.marketable_yield_kg)

    def test_delayed_harvest_under_heat_and_rain_increases_quality_risk(self):
        state = GreenhouseState(
            substrate_moisture_pct=54.0,
            drain_ec=1.9,
            disease_risk=0.36,
            ripe_fruit_ratio=0.9,
            fruit_count=100,
            leaf_density=0.68,
            ventilation_score=0.5,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.18,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=650.0,
            vpd_kpa=1.35,
            humidity_pct=88.0,
            rain_probability=80.0,
            inside_temperature_c=30.0,
        )

        step = GreenhouseSimulator().apply(state, environment, HarvestWork(pick_ratio=0.3, delayed_days=2))

        self.assertGreater(step.state.quality_risk, state.quality_risk)
        self.assertIn("delayed harvest under heat/rain increased quality risk", step.notes)

    def test_leaf_pruning_opens_canopy_and_reduces_disease_risk(self):
        state = GreenhouseState(
            substrate_moisture_pct=62.0,
            drain_ec=1.8,
            disease_risk=0.66,
            ripe_fruit_ratio=0.45,
            fruit_count=90,
            leaf_density=0.86,
            ventilation_score=0.32,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.16,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=260.0,
            vpd_kpa=0.45,
            humidity_pct=88.0,
            rain_probability=55.0,
            inside_temperature_c=24.0,
        )

        step = GreenhouseSimulator().apply(state, environment, LeafPruningWork(removal_ratio=0.18))

        self.assertLess(step.state.leaf_density, state.leaf_density)
        self.assertGreater(step.state.ventilation_score, state.ventilation_score)
        self.assertLess(step.state.disease_risk, state.disease_risk)

    def test_excessive_leaf_pruning_reduces_yield_potential(self):
        state = GreenhouseState(
            substrate_moisture_pct=60.0,
            drain_ec=1.8,
            disease_risk=0.5,
            ripe_fruit_ratio=0.4,
            fruit_count=90,
            leaf_density=0.42,
            ventilation_score=0.65,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.12,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=320.0,
            vpd_kpa=0.75,
            humidity_pct=72.0,
            rain_probability=20.0,
            inside_temperature_c=24.0,
        )

        step = GreenhouseSimulator().apply(state, environment, LeafPruningWork(removal_ratio=0.4))

        self.assertLess(step.state.yield_potential, state.yield_potential)
        self.assertIn("excessive leaf removal reduced photosynthetic area", step.notes)


if __name__ == "__main__":
    unittest.main()
