from libsbapi import (
    DiseaseControlWork,
    DistributionType,
    GreenhouseEnvironment,
    GreenhouseSimulator,
    GreenhouseState,
    HarvestWork,
    IrrigationWork,
    LeafPruningWork,
    RunnerRemovalWork,
)


def main():
    simulator = GreenhouseSimulator()
    environment = GreenhouseEnvironment(
        solar_radiation_w_m2=690.0,
        vpd_kpa=1.35,
        humidity_pct=89.0,
        rain_probability=70.0,
        inside_temperature_c=29.0,
        solar_integral_j_cm2=150.0,
        leaf_wetness_hours=7.0,
        storage_temp_c=8.0,
        month=4,
    )
    state = GreenhouseState(
        substrate_moisture_pct=48.0,
        drain_ec=2.2,
        disease_risk=0.58,
        ripe_fruit_ratio=0.78,
        fruit_count=110,
        leaf_density=0.84,
        ventilation_score=0.34,
        yield_potential=1.0,
        marketable_yield_kg=0.0,
        quality_risk=0.16,
        feed_ec=1.4,
        drainage_ratio_pct=18.0,
        substrate_vwc_m3_m3=0.17,
        coloring_pct=85.0,
        distribution_type=DistributionType.COLD_CHAIN,
        runner_count=4,
        flower_count=25,
        leaf_count=24,
        leaf_area_proxy=0.8,
        flowering_stage_pct=65.0,
        days_since_fungicide=14,
        old_or_diseased_leaf_level=0.7,
    )

    actions = (
        IrrigationWork(volume_l=2.0),
        DiseaseControlWork(effectiveness=0.55),
        RunnerRemovalWork(remove_count=3),
        LeafPruningWork(removal_ratio=0.18),
        HarvestWork(pick_ratio=0.45, delayed_days=1),
    )

    print("paper-rule greenhouse simulator")
    for action in actions:
        step = simulator.apply(state, environment, action)
        state = step.state
        print(f"\n{action.__class__.__name__}")
        print(f"  notes: {', '.join(step.notes)}")
        if step.evidence_tags:
            print(f"  evidence: {', '.join(tag.value for tag in step.evidence_tags)}")
        if step.warnings:
            print(f"  warnings: {', '.join(step.warnings)}")
        if step.metrics:
            print(
                "  metrics: "
                + ", ".join(f"{name}={value:g}" for name, value in step.metrics)
            )
        print(f"  confidence: {step.confidence:.2f}")
        print(
            "  state: "
            f"moisture={state.substrate_moisture_pct:.1f}, "
            f"drain_ec={state.drain_ec:.2f}, "
            f"disease={state.disease_risk:.2f}, "
            f"ripe={state.ripe_fruit_ratio:.2f}, "
            f"fruit={state.fruit_count}, "
            f"runner={state.runner_count}, "
            f"leaf={state.leaf_density:.2f}, "
            f"vent={state.ventilation_score:.2f}, "
            f"yield_kg={state.marketable_yield_kg:.3f}, "
            f"quality_risk={state.quality_risk:.2f}"
        )


if __name__ == "__main__":
    main()
