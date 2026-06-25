# /// script
# dependencies = []
# ///
# How to run:
#   python3 -m examples.greenhouse_scenario_compare

from libsbapi.display_labels import scenario_label
from libsbapi.greenhouse_models import GreenhouseEnvironment, GreenhouseState
from libsbapi.recommendation_generator import TEXT_KO
from libsbapi.scenario_comparison import compare_action_candidates


DISPLAY_CANDIDATES = (
    "no_irrigation",
    "irrigation",
    "lower_ec_nutrient_adjustment",
    "ventilation",
    "shading",
    "heat_preservation_heating_review",
)


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

    print("단기 Level 1 온실 관리 작업 시나리오 비교")
    print(report.not_training_label_notice)
    print(
        "후보 | 내부 action id | 기대 효과 | 위험/주의 | 에너지 비용 | 수분 | EC | 습도 | VPD | 온도 | 비고"
    )
    print("-" * 160)
    for scenario in report.scenarios:
        if scenario.action_type not in DISPLAY_CANDIDATES:
            continue
        print(
            f"{scenario_label(scenario.action_type)} | "
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
    return "; ".join(_ko(value) for value in values) if values else "-"


def _ko(value: str) -> str:
    if value.startswith("heuristic prototype comparison only"):
        return "휴리스틱 prototype 비교입니다."
    if "fake supervised farmwork labels" in value:
        return "시나리오 결과를 가짜 지도학습 라벨로 사용하지 않습니다."
    return TEXT_KO.get(value, value)


if __name__ == "__main__":
    main()
