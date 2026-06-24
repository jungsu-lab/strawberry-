# /// script
# dependencies = []
# ///
# How to run:
#   python3 -m examples.greenhouse_scenario_compare

from libsbapi.greenhouse_models import (
    DiseaseControlWork,
    GreenhouseEnvironment,
    GreenhouseState,
    HarvestWork,
    IrrigationWork,
    LeafPruningWork,
)
from libsbapi.simulation_runner import Scenario, ScheduledWork, compare_scenarios


def main() -> None:
    state = GreenhouseState(
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
        old_or_diseased_leaf_level=0.45,
    )
    environment = GreenhouseEnvironment(
        solar_radiation_w_m2=520.0,
        vpd_kpa=0.38,
        humidity_pct=89.0,
        rain_probability=55.0,
        inside_temperature_c=25.0,
        leaf_wetness_hours=5.0,
    )
    comparison = compare_scenarios(
        (
            Scenario(
                name="irrigation focused",
                initial_state=state,
                environment=environment,
                days=5,
                schedule=(ScheduledWork(day=1, work=IrrigationWork(volume_l=1.2)),),
            ),
            Scenario(
                name="control and pruning",
                initial_state=state,
                environment=environment,
                days=5,
                schedule=(
                    ScheduledWork(day=1, work=DiseaseControlWork(effectiveness=0.55)),
                    ScheduledWork(day=2, work=LeafPruningWork(removal_ratio=0.18)),
                ),
            ),
            Scenario(
                name="harvest now",
                initial_state=state,
                environment=environment,
                days=5,
                schedule=(ScheduledWork(day=1, work=HarvestWork(pick_ratio=0.45)),),
            ),
        ),
    )

    print("scenario comparison")
    for record in comparison.end_states:
        message = (
            f"{record.scenario}: yield={record.marketable_yield_kg:.3f}kg, "
            + f"disease={record.disease_risk:.2f}, quality={record.quality_risk:.2f}, "
            + f"moisture={record.substrate_moisture_pct:.1f}%"
        )
        print(message)


if __name__ == "__main__":
    main()
