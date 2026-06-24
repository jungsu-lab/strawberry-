from __future__ import annotations

import json
from pathlib import Path

from .berrynext import GreenhouseSnapshot
from .daily_context_builder import DailyContextRecord
from .farmwork import DailyFarmWorkDecisionEngine, DailyFarmWorkPlan, FarmWorkHistory

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]


def write_daily_context_files(records: list[DailyContextRecord], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for record in records:
        path = output_dir / record.output_name()
        with path.open("w", encoding="utf-8") as file:
            json.dump(_record_to_json(record), file, ensure_ascii=False, indent=2)
            file.write("\n")
        paths.append(path)
    return paths


def write_recommendation_log(records: list[DailyContextRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    engine = DailyFarmWorkDecisionEngine()
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            payload = _plan_to_json(record, engine.plan_today(record.context))
            file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            file.write("\n")


def _plan_to_json(record: DailyContextRecord, plan: DailyFarmWorkPlan) -> JsonObject:
    return {
        "farm_id": record.farm_id,
        "date": record.day.isoformat(),
        "summary": plan.summary,
        "tasks": [
            {
                "work_type": task.work_type.value,
                "timing": task.timing.value,
                "priority": task.priority,
                "score": task.score,
                "title": task.title,
                "reason": task.reason,
                "safeguards": list(task.safeguards),
                "metrics": dict(task.metrics),
            }
            for task in plan.tasks
        ],
        "data_sources": list(plan.data_sources),
    }


def _record_to_json(record: DailyContextRecord) -> JsonObject:
    context = record.context
    return {
        "farm_id": record.farm_id,
        "date": record.day.isoformat(),
        "growth_stage": context.growth_stage.value,
        "snapshot": _snapshot_to_json(context.snapshot),
        "history": _history_to_json(context.history),
        "source_files": list(record.source_files),
    }


def _snapshot_to_json(snapshot: GreenhouseSnapshot) -> JsonObject:
    return {
        "inside_temperature_c": snapshot.inside_temperature_c,
        "inside_humidity_pct": snapshot.inside_humidity_pct,
        "co2_ppm": snapshot.co2_ppm,
        "solar_radiation_w_m2": snapshot.solar_radiation_w_m2,
        "root_zone_moisture_pct": snapshot.root_zone_moisture_pct,
        "ec": snapshot.ec,
        "ph": snapshot.ph,
        "vent_open_pct": snapshot.vent_open_pct,
        "weather": {"rain_probability": snapshot.weather.rain_probability},
        "image": {
            "fruit_count": snapshot.image.fruit_count,
            "leaf_density": snapshot.image.leaf_density,
        },
    }


def _history_to_json(history: FarmWorkHistory) -> JsonObject:
    return {
        "days_since_scouting": history.days_since_scouting,
    }
