from libsbapi import (
    CropGrowthStage,
    DailyFarmWorkDecisionEngine,
    FarmWorkContext,
    FarmWorkHistory,
    GreenhouseSnapshot,
    ImageGrowthSignals,
    WeatherForecast,
)


def main():
    context = FarmWorkContext(
        growth_stage=CropGrowthStage.HARVEST,
        snapshot=GreenhouseSnapshot(
            inside_temperature_c=27.5,
            inside_humidity_pct=91.0,
            solar_radiation_w_m2=540.0,
            root_zone_moisture_pct=31.0,
            ec=1.3,
            ph=6.0,
            vent_open_pct=8.0,
            weather=WeatherForecast(rain_probability=75.0, expected_rain_mm=7.0),
            image=ImageGrowthSignals(
                ripe_fruit_ratio=0.86,
                average_fruit_size_mm=31.0,
                fruit_count=52,
                leaf_density=0.88,
                disease_spot_ratio=0.04,
            ),
        ),
        history=FarmWorkHistory(
            days_since_irrigation=2,
            days_since_scouting=5,
            days_since_disease_control=11,
            days_since_harvest=3,
            days_since_leaf_pruning=12,
        ),
    )

    plan = DailyFarmWorkDecisionEngine().plan_today(context)
    print(plan.summary)
    print("data:", ", ".join(plan.data_sources))
    print("Level 1 recommendations:")
    for task in plan.tasks:
        print(f"[{task.priority}] {task.title} ({task.timing}) score={task.score}")
        print(f"  reason: {task.reason}")
        if task.safeguards:
            print(f"  safeguards: {', '.join(task.safeguards)}")
    if plan.auxiliary_alerts:
        print("Auxiliary alerts:")
        for alert in plan.auxiliary_alerts:
            print(f"[{alert.priority}] {alert.title} ({alert.timing}) score={alert.score}")
            print(f"  reason: {alert.reason}")
            if alert.safeguards:
                print(f"  safeguards: {', '.join(alert.safeguards)}")


if __name__ == "__main__":
    main()
