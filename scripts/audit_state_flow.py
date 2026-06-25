from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from libsbapi.offline_demo import SAMPLE_CONTEXT, _environment_from_current, _greenhouse_state_from_current, build_demo


WATCH_VARIABLES = (
    "air_temp",
    "humidity",
    "vpd",
    "solar_radiation",
    "substrate_moisture",
    "root_zone_moisture",
    "feed_ec",
    "drain_ec",
    "root_ec",
)


def main() -> None:
    context_path = SAMPLE_CONTEXT
    demo = build_demo(context_path)
    raw = _load_raw_snapshot(context_path)
    current = demo.current_state
    scenario_state = _greenhouse_state_from_current(current)
    scenario_environment = _environment_from_current(current)
    predictions_1h = {item.target: item for item in demo.predictions if item.horizon_hours == 1}
    scores = {item.action_type: item for item in demo.work_scores}
    dashboard_values = _dashboard_values(current)

    print("BerryNext state flow audit")
    print(f"context={context_path}")
    print(
        "variable | raw_input | current_state | prediction_input | predicted_state | "
        "scenario_input | scorer_input | dashboard_value | notes"
    )
    print("-" * 150)
    for variable in WATCH_VARIABLES:
        prediction = predictions_1h.get(variable)
        print(
            " | ".join(
                (
                    variable,
                    _fmt(_raw_value(raw, variable)),
                    _fmt(getattr(current, variable, None)),
                    _fmt(prediction.current_value if prediction else None),
                    _fmt(prediction.predicted_value if prediction else None),
                    _fmt(_scenario_value(variable, scenario_state, scenario_environment)),
                    _fmt(_scorer_value(variable, current, scores)),
                    _fmt(dashboard_values.get(variable)),
                    _notes(variable, current, prediction),
                )
            )
        )
    if current.quality_warnings:
        print("\ndata_quality_warnings")
        for warning in current.quality_warnings:
            print(f"- {warning}")
    if demo.scenario_input_warnings:
        print("\nscenario_input_warnings")
        for warning in demo.scenario_input_warnings:
            print(f"- {warning}")


def _load_raw_snapshot(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    snapshot = payload.get("snapshot", {})
    return snapshot if isinstance(snapshot, dict) else {}


def _raw_value(snapshot: dict, variable: str) -> object:
    aliases = {
        "air_temp": ("air_temp", "inside_temperature_c", "temperature_c"),
        "humidity": ("humidity", "inside_humidity_pct", "humidity_pct"),
        "vpd": ("vpd", "vpd_kpa"),
        "solar_radiation": ("solar_radiation", "solar_radiation_w_m2", "radiation_w_m2"),
        "substrate_moisture": ("substrate_moisture", "substrate_moisture_pct"),
        "root_zone_moisture": ("root_zone_moisture", "root_zone_moisture_pct"),
        "feed_ec": ("feed_ec",),
        "drain_ec": ("drain_ec", "drainage_ec", "ec"),
        "root_ec": ("root_ec", "root_zone_ec"),
    }[variable]
    for alias in aliases:
        if alias in snapshot:
            return snapshot[alias]
    return None


def _scenario_value(variable: str, scenario_state, scenario_environment) -> object:
    mapping = {
        "air_temp": scenario_environment.inside_temperature_c,
        "humidity": scenario_environment.humidity_pct,
        "vpd": scenario_environment.vpd_kpa,
        "solar_radiation": scenario_environment.solar_radiation_w_m2,
        "substrate_moisture": scenario_state.substrate_moisture_pct,
        "root_zone_moisture": scenario_state.substrate_moisture_pct,
        "feed_ec": scenario_state.feed_ec,
        "drain_ec": scenario_state.drain_ec,
        "root_ec": None,
    }
    return mapping[variable]


def _scorer_value(variable: str, current, scores: dict) -> object:
    if variable in {"substrate_moisture", "root_zone_moisture"}:
        return f"{current.root_zone_moisture} -> irrigation {scores['irrigation'].score:.0f}"
    if variable in {"feed_ec", "drain_ec", "root_ec"}:
        return f"{getattr(current, variable)} -> EC {scores['nutrient_ec_check'].score:.0f}"
    if variable in {"humidity", "vpd"}:
        return f"{getattr(current, variable)} -> ventilation {scores['ventilation_dehumidification'].score:.0f}"
    if variable in {"air_temp", "solar_radiation"}:
        return f"{getattr(current, variable)} -> shading {scores['shading_high_temperature'].score:.0f}"
    return getattr(current, variable, None)


def _dashboard_values(current) -> dict[str, object]:
    return {variable: getattr(current, variable, None) for variable in WATCH_VARIABLES}


def _notes(variable: str, current, prediction) -> str:
    notes: list[str] = []
    if variable in current.missing_fields:
        notes.append("missing")
    if variable in current.fallback_fields:
        notes.append("proxy/fallback")
    if prediction is not None and prediction.fallback_used:
        notes.append(f"prediction fallback: {prediction.fallback_reason}")
    if variable == "root_ec" and current.root_ec is None and current.drain_ec is not None:
        notes.append("EC scorer can use drain_ec while root_ec is missing")
    return "; ".join(notes) if notes else "-"


def _fmt(value: object) -> str:
    if value is None:
        return "데이터 없음"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


if __name__ == "__main__":
    main()
