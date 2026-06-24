import unittest

from libsbapi.greenhouse_simulator import (
    DiseaseControlMethod,
    DiseaseControlWork,
    DistributionType,
    EvidenceTag,
    GreenhouseEnvironment,
    GreenhouseSimulator,
    GreenhouseState,
    HarvestWork,
    IrrigationWork,
    LeafPruningWork,
    RunnerRemovalWork,
)


class GreenhouseSimulatorPaperRulesTest(unittest.TestCase):
    def test_irrigation_logs_ec_and_drainage_warnings_when_salts_accumulate(self):
        state = GreenhouseState(
            substrate_moisture_pct=55.0,
            drain_ec=2.2,
            disease_risk=0.3,
            ripe_fruit_ratio=0.3,
            fruit_count=50,
            leaf_density=0.7,
            ventilation_score=0.5,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.1,
            feed_ec=1.4,
            drainage_ratio_pct=18.0,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=520.0,
            vpd_kpa=1.25,
            humidity_pct=70.0,
            rain_probability=15.0,
            inside_temperature_c=26.0,
            solar_integral_j_cm2=150.0,
        )

        step = GreenhouseSimulator().apply(state, environment, IrrigationWork(volume_l=1.0))

        self.assertIn(EvidenceTag.IRRIGATION_SOLAR_MOISTURE, step.evidence_tags)
        self.assertIn(EvidenceTag.IRRIGATION_EC_DRAINAGE, step.evidence_tags)
        self.assertIn("drain EC stayed high versus feed EC", step.warnings)
        self.assertIn("drainage ratio is below the Seolhyang 40-50% target", step.warnings)

    def test_seolhyang_feed_ec_warning_uses_own_range(self):
        state = GreenhouseState(
            substrate_moisture_pct=58.0,
            drain_ec=1.7,
            disease_risk=0.22,
            ripe_fruit_ratio=0.2,
            fruit_count=40,
            leaf_density=0.65,
            ventilation_score=0.55,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.08,
            feed_ec=1.7,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=300.0,
            vpd_kpa=0.75,
            humidity_pct=72.0,
            rain_probability=10.0,
            inside_temperature_c=24.0,
        )

        step = GreenhouseSimulator().apply(state, environment, IrrigationWork(volume_l=0.5))

        self.assertIn(EvidenceTag.NUTRIENT_SEOLHYANG_EC, step.evidence_tags)
        self.assertIn("Seolhyang feed EC is above the 0.8-1.5 dS/m candidate range", step.warnings)

    def test_low_vwc_reduces_yield_potential_and_logs_deficit_irrigation_risk(self):
        state = GreenhouseState(
            substrate_moisture_pct=45.0,
            drain_ec=1.4,
            disease_risk=0.2,
            ripe_fruit_ratio=0.2,
            fruit_count=60,
            leaf_density=0.72,
            ventilation_score=0.5,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.08,
            substrate_vwc_m3_m3=0.16,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=620.0,
            vpd_kpa=1.1,
            humidity_pct=68.0,
            rain_probability=10.0,
            inside_temperature_c=25.0,
        )

        step = GreenhouseSimulator().apply(state, environment, IrrigationWork(volume_l=0.0))

        self.assertLess(step.state.yield_potential, state.yield_potential)
        self.assertIn(EvidenceTag.IRRIGATION_VWC_SENSOR, step.evidence_tags)
        self.assertIn("VWC is below the Seolhyang deficit-irrigation reference", step.warnings)

    def test_disease_control_keeps_pressure_when_sixty_percent_bloom_is_wet(self):
        state = GreenhouseState(
            substrate_moisture_pct=63.0,
            drain_ec=1.7,
            disease_risk=0.78,
            ripe_fruit_ratio=0.2,
            fruit_count=65,
            leaf_density=0.82,
            ventilation_score=0.28,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.12,
            flowering_stage_pct=65.0,
            days_since_fungicide=14,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=160.0,
            vpd_kpa=0.28,
            humidity_pct=93.0,
            rain_probability=80.0,
            inside_temperature_c=20.0,
            leaf_wetness_hours=8.0,
        )

        step = GreenhouseSimulator().apply(
            state,
            environment,
            DiseaseControlWork(effectiveness=0.55, method=DiseaseControlMethod.FUNGICIDE),
        )

        self.assertIn(EvidenceTag.DISEASE_BOTRYTIS_FLOWERING, step.evidence_tags)
        self.assertIn(EvidenceTag.DISEASE_ADVISORY_SYSTEM, step.evidence_tags)
        self.assertIn("flowering and wet canopy kept Botrytis pressure high", step.notes)
        self.assertGreater(step.state.disease_risk, 0.3)

    def test_ozonated_water_has_low_control_confidence(self):
        state = GreenhouseState(
            substrate_moisture_pct=64.0,
            drain_ec=1.8,
            disease_risk=0.72,
            ripe_fruit_ratio=0.3,
            fruit_count=70,
            leaf_density=0.78,
            ventilation_score=0.35,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.18,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=140.0,
            vpd_kpa=0.32,
            humidity_pct=91.0,
            rain_probability=65.0,
            inside_temperature_c=21.0,
            leaf_wetness_hours=7.0,
        )

        step = GreenhouseSimulator().apply(
            state,
            environment,
            DiseaseControlWork(effectiveness=0.8, method=DiseaseControlMethod.OZONATED_WATER),
        )

        self.assertLess(step.confidence, 0.8)
        self.assertIn("ozonated water is low-confidence for Botrytis control", step.warnings)

    def test_cold_chain_harvest_penalizes_eighty_five_percent_coloring(self):
        state = GreenhouseState(
            substrate_moisture_pct=55.0,
            drain_ec=1.7,
            disease_risk=0.28,
            ripe_fruit_ratio=0.85,
            fruit_count=100,
            leaf_density=0.7,
            ventilation_score=0.52,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.1,
            coloring_pct=85.0,
            distribution_type=DistributionType.COLD_CHAIN,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=420.0,
            vpd_kpa=0.95,
            humidity_pct=72.0,
            rain_probability=20.0,
            inside_temperature_c=24.0,
            storage_temp_c=8.0,
        )

        step = GreenhouseSimulator().apply(state, environment, HarvestWork(pick_ratio=0.5))

        self.assertIn(EvidenceTag.HARVEST_SEOLHYANG_COLORING, step.evidence_tags)
        self.assertIn("cold-chain harvest below 90% coloring has marketability risk", step.warnings)
        self.assertIn(("expected_days_to_100_coloring", 3.0), step.metrics)
        self.assertGreater(step.state.quality_risk, state.quality_risk)

    def test_runner_removal_reduces_runner_sink_and_improves_yield_potential(self):
        state = GreenhouseState(
            substrate_moisture_pct=57.0,
            drain_ec=1.7,
            disease_risk=0.25,
            ripe_fruit_ratio=0.4,
            fruit_count=95,
            leaf_density=0.74,
            ventilation_score=0.48,
            yield_potential=0.88,
            marketable_yield_kg=0.0,
            quality_risk=0.12,
            runner_count=6,
            flower_count=30,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=460.0,
            vpd_kpa=0.9,
            humidity_pct=75.0,
            rain_probability=10.0,
            inside_temperature_c=25.0,
        )

        step = GreenhouseSimulator().apply(state, environment, RunnerRemovalWork(remove_count=4))

        self.assertEqual(step.state.runner_count, 2)
        self.assertGreater(step.state.yield_potential, state.yield_potential)
        self.assertIn(EvidenceTag.CANOPY_RUNNER_REMOVAL, step.evidence_tags)

    def test_leaf_pruning_with_low_leaf_count_is_warned_and_penalized(self):
        state = GreenhouseState(
            substrate_moisture_pct=60.0,
            drain_ec=1.8,
            disease_risk=0.5,
            ripe_fruit_ratio=0.45,
            fruit_count=105,
            leaf_density=0.44,
            ventilation_score=0.6,
            yield_potential=1.0,
            marketable_yield_kg=0.0,
            quality_risk=0.12,
            leaf_count=16,
            leaf_area_proxy=0.35,
            old_or_diseased_leaf_level=0.2,
        )
        environment = GreenhouseEnvironment(
            solar_radiation_w_m2=350.0,
            vpd_kpa=0.8,
            humidity_pct=76.0,
            rain_probability=20.0,
            inside_temperature_c=24.0,
        )

        step = GreenhouseSimulator().apply(state, environment, LeafPruningWork(removal_ratio=0.22))

        self.assertIn(EvidenceTag.CANOPY_DEFOLIATION_LIMIT, step.evidence_tags)
        self.assertIn("leaf count is already low; avoid normal-leaf defoliation", step.warnings)
        self.assertLess(step.state.yield_potential, state.yield_potential)


if __name__ == "__main__":
    unittest.main()
