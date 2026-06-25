# /// script
# dependencies = []
# ///
# How to run:
#   python3 -m examples.greenhouse_scenario_compare

from libsbapi.greenhouse_models import GreenhouseEnvironment, GreenhouseState
from libsbapi.scenario_comparison import compare_action_candidates


def main() -> None:
    state = GreenhouseState(
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
    environment = GreenhouseEnvironment(
        solar_radiation_w_m2=720.0,
        vpd_kpa=1.35,
        humidity_pct=91.0,
        rain_probability=65.0,
        inside_temperature_c=29.0,
        leaf_wetness_hours=6.0,
    )
    report = compare_action_candidates(state, environment, horizon_hours=3)

    print("short-horizon greenhouse action candidate comparison")
    print(report.not_training_label_notice)
    print(
        "candidate | expected benefit | risk | energy cost | moisture | EC | humidity | VPD | temp | notes"
    )
    print("-" * 132)
    for scenario in report.scenarios:
        print(
            f"{scenario.action_type} | "
            f"{_join(scenario.expected_benefits)} | "
            f"{_join(scenario.risks)} | "
            f"{scenario.energy_cost_delta:+.1f} | "
            f"{scenario.moisture_delta:+.1f} | "
            f"{scenario.ec_delta:+.2f} | "
            f"{scenario.humidity_delta:+.1f} | "
            f"{scenario.vpd_delta:+.2f} | "
            f"{scenario.temperature_delta:+.1f} | "
            f"{_join(scenario.notes)}"
        )


def _join(values: tuple[str, ...]) -> str:
    return "; ".join(values) if values else "-"


if __name__ == "__main__":
    main()
