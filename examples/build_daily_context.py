from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Final

from libsbapi import (
    CropGrowthStage,
    DailyFarmWorkDecisionEngine,
    DailyFarmWorkPlan,
    FarmWorkContext,
    FarmWorkHistory,
    GreenhouseSnapshot,
    ImageGrowthSignals,
    WeatherForecast,
)

DEFAULT_CONTEXT_PATH: Final = Path(__file__).with_name("sample_daily_context.json")
JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]


class ContextParseError(ValueError):
    pass


def _json_object(value: JsonValue, field_name: str) -> JsonObject:
    match value:
        case dict():
            return value
        case _:
            raise ContextParseError(f"{field_name} must be an object")


def _optional_float(data: JsonObject, field_name: str) -> float | None:
    value = data.get(field_name)
    match value:
        case None:
            return None
        case bool():
            raise ContextParseError(f"{field_name} must be a number")
        case int() | float():
            return float(value)
        case _:
            raise ContextParseError(f"{field_name} must be a number")


def _optional_int(data: JsonObject, field_name: str) -> int | None:
    value = data.get(field_name)
    match value:
        case None:
            return None
        case bool():
            raise ContextParseError(f"{field_name} must be an integer")
        case int():
            return value
        case _:
            raise ContextParseError(f"{field_name} must be an integer")


def _optional_bool(data: JsonObject, field_name: str) -> bool | None:
    value = data.get(field_name)
    match value:
        case None:
            return None
        case bool():
            return value
        case _:
            raise ContextParseError(f"{field_name} must be a boolean")


def _growth_stage(data: JsonObject) -> CropGrowthStage:
    value = data.get("growth_stage")
    match value:
        case str():
            try:
                return CropGrowthStage(value)
            except ValueError as error:
                raise ContextParseError("growth_stage is not supported") from error
        case _:
            raise ContextParseError("growth_stage must be a string")


def _weather(data: JsonObject) -> WeatherForecast:
    weather = _json_object(data.get("weather", {}), "snapshot.weather")
    return WeatherForecast(
        rain_probability=_optional_float(weather, "rain_probability"),
        expected_rain_mm=_optional_float(weather, "expected_rain_mm"),
        min_temperature_c=_optional_float(weather, "min_temperature_c"),
        max_temperature_c=_optional_float(weather, "max_temperature_c"),
        solar_radiation_mj=_optional_float(weather, "solar_radiation_mj"),
    )


def _image(data: JsonObject) -> ImageGrowthSignals:
    image = _json_object(data.get("image", {}), "snapshot.image")
    return ImageGrowthSignals(
        ripe_fruit_ratio=_optional_float(image, "ripe_fruit_ratio"),
        average_fruit_size_mm=_optional_float(image, "average_fruit_size_mm"),
        fruit_count=_optional_int(image, "fruit_count"),
        leaf_density=_optional_float(image, "leaf_density"),
        disease_spot_ratio=_optional_float(image, "disease_spot_ratio"),
    )


def _snapshot(data: JsonObject) -> GreenhouseSnapshot:
    snapshot = _json_object(data.get("snapshot"), "snapshot")
    return GreenhouseSnapshot(
        inside_temperature_c=_optional_float(snapshot, "inside_temperature_c"),
        inside_humidity_pct=_optional_float(snapshot, "inside_humidity_pct"),
        co2_ppm=_optional_float(snapshot, "co2_ppm"),
        solar_radiation_w_m2=_optional_float(snapshot, "solar_radiation_w_m2"),
        root_zone_moisture_pct=_optional_float(snapshot, "root_zone_moisture_pct"),
        ec=_optional_float(snapshot, "ec"),
        ph=_optional_float(snapshot, "ph"),
        supply_ml=_optional_float(snapshot, "supply_ml"),
        drain_ml=_optional_float(snapshot, "drain_ml"),
        vent_open_pct=_optional_float(snapshot, "vent_open_pct"),
        fog_on=_optional_bool(snapshot, "fog_on"),
        heating_on=_optional_bool(snapshot, "heating_on"),
        energy_kwh_today=_optional_float(snapshot, "energy_kwh_today"),
        weather=_weather(snapshot),
        image=_image(snapshot),
    )


def _history(data: JsonObject) -> FarmWorkHistory:
    history = _json_object(data.get("history", {}), "history")
    return FarmWorkHistory(
        days_since_irrigation=_optional_int(history, "days_since_irrigation"),
        days_since_scouting=_optional_int(history, "days_since_scouting"),
        days_since_disease_control=_optional_int(history, "days_since_disease_control"),
        days_since_harvest=_optional_int(history, "days_since_harvest"),
        days_since_leaf_pruning=_optional_int(history, "days_since_leaf_pruning"),
    )


def context_from_json_file(path: Path) -> FarmWorkContext:
    with path.open(encoding="utf-8") as file:
        raw = json.load(file)
    data = _json_object(raw, "root")
    return FarmWorkContext(
        growth_stage=_growth_stage(data),
        snapshot=_snapshot(data),
        history=_history(data),
    )


def plan_from_json_file(path: Path) -> DailyFarmWorkPlan:
    context = context_from_json_file(path)
    return DailyFarmWorkDecisionEngine().plan_today(context)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONTEXT_PATH
    plan = plan_from_json_file(path)
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
