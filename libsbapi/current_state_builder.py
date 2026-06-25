from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

from .berrynext import compute_vpd_kpa
from .decision_contract import CurrentGreenhouseState
from .farmwork import FarmWorkContext


JsonObject = dict[str, Any]

STATE_FIELDS: Final = (
    "air_temp",
    "humidity",
    "vpd",
    "co2",
    "solar_radiation",
    "substrate_moisture",
    "root_zone_moisture",
    "feed_ec",
    "drain_ec",
    "root_ec",
    "feed_ph",
    "drain_ph",
    "drainage_ratio",
    "outside_temp",
    "outside_humidity",
    "growth_stage",
    "time_of_day",
    "timestamp",
)
AMBIGUOUS_ZERO_FIELDS: Final = {
    "humidity",
    "co2",
    "substrate_moisture",
    "root_zone_moisture",
    "feed_ec",
    "drain_ec",
    "root_ec",
    "feed_ph",
    "drain_ph",
    "drainage_ratio",
    "outside_humidity",
}
ASSUMED_UNITS: Final[dict[str, str]] = {
    "air_temp": "degC",
    "humidity": "percent",
    "vpd": "kPa",
    "co2": "ppm",
    "solar_radiation": "W/m2",
    "cumulative_solar_radiation": "source unit",
    "substrate_moisture": "percent",
    "root_zone_moisture": "percent",
    "feed_ec": "dS/m",
    "drain_ec": "dS/m",
    "root_ec": "dS/m",
    "feed_ph": "pH",
    "drain_ph": "pH",
    "drainage_ratio": "percent",
    "outside_temp": "degC",
    "outside_humidity": "percent",
}


@dataclass(frozen=True, slots=True)
class CurrentStateBuilder:
    stale_after_hours: float = 48.0
    now: datetime | None = None

    def from_daily_context_file(self, path: Path) -> CurrentGreenhouseState:
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
        source_label = path.stem
        if path.name == "sample_daily_context.json":
            source_label = "sample_daily_context"
        return self.from_daily_context(_object(payload), source_label=source_label)

    def from_daily_context(
        self,
        payload: JsonObject,
        source_label: str = "daily_context",
    ) -> CurrentGreenhouseState:
        snapshot = _object(payload.get("snapshot", {}))
        weather = _object(snapshot.get("weather", {}))
        timestamp = _optional_str(payload, "timestamp") or _optional_str(snapshot, "timestamp")
        air_temp = _first_float(snapshot, "air_temp", "inside_temperature_c", "temperature_c")
        humidity = _first_float(snapshot, "humidity", "inside_humidity_pct", "humidity_pct")
        vpd = _first_float(snapshot, "vpd", "vpd_kpa")
        fallback_fields: list[str] = []
        warnings: list[str] = []
        if vpd is None and air_temp is not None and humidity is not None:
            vpd = round(compute_vpd_kpa(air_temp, humidity) or 0.0, 3)
            fallback_fields.append("vpd")
            warnings.append("vpd calculated from air temperature and humidity")

        outside_temp = _first_float(snapshot, "outside_temp", "outside_temperature_c")
        if outside_temp is None:
            outside_temp = _first_float(weather, "outside_temp", "outside_temperature_c")
        outside_humidity = _first_float(snapshot, "outside_humidity", "outside_humidity_pct")
        if outside_humidity is None:
            outside_humidity = _first_float(weather, "outside_humidity", "outside_humidity_pct")
        sensor_quality = _str_mapping(payload.get("sensor_quality")) | _str_mapping(snapshot.get("sensor_quality"))
        values = {
            "timestamp": timestamp,
            "air_temp": air_temp,
            "humidity": humidity,
            "vpd": vpd,
            "co2": _first_float(snapshot, "co2", "co2_ppm"),
            "solar_radiation": _first_float(snapshot, "solar_radiation", "solar_radiation_w_m2", "radiation_w_m2"),
            "cumulative_solar_radiation": _first_float(
                snapshot,
                "cumulative_solar_radiation",
                "cumulative_radiation_j_cm2",
                "solar_integral_j_cm2",
            ),
            "substrate_moisture": _first_float(snapshot, "substrate_moisture", "substrate_moisture_pct"),
            "root_zone_moisture": _first_float(snapshot, "root_zone_moisture", "root_zone_moisture_pct"),
            "feed_ec": _first_float(snapshot, "feed_ec"),
            "drain_ec": _first_float(snapshot, "drain_ec", "drainage_ec", "ec"),
            "root_ec": _first_float(snapshot, "root_ec", "root_zone_ec"),
            "feed_ph": _first_float(snapshot, "feed_ph"),
            "drain_ph": _first_float(snapshot, "drain_ph", "drainage_ph", "ph"),
            "drainage_ratio": _first_float(snapshot, "drainage_ratio", "drainage_ratio_pct"),
            "outside_temp": outside_temp,
            "outside_humidity": outside_humidity,
            "growth_stage": _optional_str(payload, "growth_stage") or _optional_str(snapshot, "growth_stage"),
            "time_of_day": _optional_str(payload, "time_of_day") or _time_of_day(timestamp),
        }
        if values["root_zone_moisture"] is None and values["substrate_moisture"] is not None:
            values["root_zone_moisture"] = values["substrate_moisture"]
            fallback_fields.append("root_zone_moisture")
            warnings.append("root_zone_moisture missing, using substrate_moisture as proxy")
        if values["substrate_moisture"] is None and values["root_zone_moisture"] is not None:
            values["substrate_moisture"] = values["root_zone_moisture"]
            fallback_fields.append("substrate_moisture")
            warnings.append("substrate_moisture missing, using root_zone_moisture as proxy")
        missing_fields = tuple(field for field in STATE_FIELDS if values.get(field) is None)
        suspicious_fields = _suspicious_zero_fields(values)
        warnings.extend(f"{field} missing" for field in missing_fields)
        warnings.extend(f"{field} is zero; verify sensor validity" for field in suspicious_fields)
        return CurrentGreenhouseState(
            timestamp=timestamp,
            air_temp=values["air_temp"],
            humidity=values["humidity"],
            vpd=values["vpd"],
            co2=values["co2"],
            solar_radiation=values["solar_radiation"],
            cumulative_solar_radiation=values["cumulative_solar_radiation"],
            substrate_moisture=values["substrate_moisture"],
            root_zone_moisture=values["root_zone_moisture"],
            feed_ec=values["feed_ec"],
            drain_ec=values["drain_ec"],
            root_ec=values["root_ec"],
            feed_ph=values["feed_ph"],
            drain_ph=values["drain_ph"],
            drainage_ratio=values["drainage_ratio"],
            outside_temp=values["outside_temp"],
            outside_humidity=values["outside_humidity"],
            growth_stage=values["growth_stage"],
            time_of_day=values["time_of_day"],
            sensor_quality=sensor_quality,
            missing_fields=missing_fields,
            fallback_fields=tuple(fallback_fields),
            suspicious_fields=suspicious_fields,
            assumed_units=ASSUMED_UNITS.copy(),
            stale_timestamp=self._stale_timestamp(timestamp),
            source_labels=(source_label,),
            quality_warnings=tuple(warnings),
        )

    def from_farmwork_context(self, context: FarmWorkContext) -> CurrentGreenhouseState:
        state = self.from_greenhouse_snapshot(context.snapshot, source_label="farmwork_context")
        return _replace_growth_stage(state, context.growth_stage.value)

    def from_greenhouse_snapshot(
        self,
        snapshot: object,
        source_label: str = "greenhouse_snapshot",
    ) -> CurrentGreenhouseState:
        if hasattr(snapshot, "sensor_state"):
            return self._from_decision_snapshot(snapshot, source_label)
        payload = {
            "snapshot": {
                "inside_temperature_c": getattr(snapshot, "inside_temperature_c", None),
                "inside_humidity_pct": getattr(snapshot, "inside_humidity_pct", None),
                "co2_ppm": getattr(snapshot, "co2_ppm", None),
                "solar_radiation_w_m2": getattr(snapshot, "solar_radiation_w_m2", None),
                "root_zone_moisture_pct": getattr(snapshot, "root_zone_moisture_pct", None),
                "ec": getattr(snapshot, "ec", None),
                "ph": getattr(snapshot, "ph", None),
            }
        }
        weather = getattr(snapshot, "weather", None)
        if weather is not None:
            payload["snapshot"]["weather"] = {
                "outside_temperature_c": getattr(weather, "outside_temperature_c", None),
                "outside_humidity_pct": getattr(weather, "outside_humidity_pct", None),
            }
        return self.from_daily_context(payload, source_label=source_label)

    def _from_decision_snapshot(self, snapshot: object, source_label: str) -> CurrentGreenhouseState:
        nutrient = getattr(snapshot, "nutrient_state", None)
        weather = getattr(snapshot, "weather_state", None)
        payload = {
            "timestamp": getattr(snapshot, "timestamp", None),
            "growth_stage": getattr(snapshot, "growth_stage", None),
            "snapshot": {
                "temperature_c": getattr(snapshot, "temperature_c", None),
                "humidity_pct": getattr(snapshot, "humidity_pct", None),
                "vpd_kpa": getattr(snapshot, "vpd_kpa", None),
                "co2_ppm": getattr(snapshot, "co2_ppm", None),
                "radiation_w_m2": getattr(snapshot, "radiation_w_m2", None),
                "cumulative_radiation_j_cm2": getattr(snapshot, "cumulative_radiation_j_cm2", None),
                "substrate_moisture_pct": getattr(snapshot, "substrate_moisture_pct", None),
                "feed_ec": getattr(nutrient, "feed_ec", None),
                "root_zone_ec": getattr(snapshot, "root_zone_ec", None),
                "drainage_ec": getattr(snapshot, "drainage_ec", None),
                "feed_ph": getattr(nutrient, "feed_ph", None),
                "root_zone_ph": getattr(snapshot, "root_zone_ph", None),
                "drainage_ph": getattr(snapshot, "drainage_ph", None),
                "drainage_ratio_pct": getattr(nutrient, "drainage_ratio_pct", None),
                "weather": {
                    "outside_temperature_c": getattr(weather, "outside_temperature_c", None),
                    "outside_humidity_pct": getattr(weather, "outside_humidity_pct", None),
                },
            },
        }
        return self.from_daily_context(payload, source_label=source_label)

    def _stale_timestamp(self, timestamp: str | None) -> bool | None:
        if timestamp is None:
            return None
        parsed = _parse_datetime(timestamp)
        if parsed is None:
            return None
        now = self.now or datetime.now(timezone.utc)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return (now.astimezone(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() > (
            self.stale_after_hours * 3600.0
        )


def _object(value: object) -> JsonObject:
    return value if isinstance(value, dict) else {}


def _optional_str(data: JsonObject, field_name: str) -> str | None:
    value = data.get(field_name)
    return value if isinstance(value, str) and value.strip() else None


def _first_float(data: JsonObject, *field_names: str) -> float | None:
    for field_name in field_names:
        value = data.get(field_name)
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            return float(value)
    return None


def _str_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, item in value.items():
        if isinstance(key, str) and isinstance(item, str) and key.strip() and item.strip():
            result[key] = item
    return result


def _time_of_day(timestamp: str | None) -> str | None:
    parsed = _parse_datetime(timestamp)
    if parsed is None:
        return None
    hour = parsed.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "night"


def _parse_datetime(timestamp: str | None) -> datetime | None:
    if timestamp is None:
        return None
    try:
        return datetime.fromisoformat(timestamp)
    except ValueError:
        return None


def _suspicious_zero_fields(values: JsonObject) -> tuple[str, ...]:
    return tuple(
        field for field in AMBIGUOUS_ZERO_FIELDS if values.get(field) == 0.0
    )


def _replace_growth_stage(state: CurrentGreenhouseState, growth_stage: str) -> CurrentGreenhouseState:
    missing_fields = tuple(field for field in state.missing_fields if field != "growth_stage")
    warnings = tuple(warning for warning in state.quality_warnings if warning != "growth_stage missing")
    return CurrentGreenhouseState(
        timestamp=state.timestamp,
        air_temp=state.air_temp,
        humidity=state.humidity,
        vpd=state.vpd,
        co2=state.co2,
        solar_radiation=state.solar_radiation,
        cumulative_solar_radiation=state.cumulative_solar_radiation,
        substrate_moisture=state.substrate_moisture,
        root_zone_moisture=state.root_zone_moisture,
        feed_ec=state.feed_ec,
        drain_ec=state.drain_ec,
        root_ec=state.root_ec,
        feed_ph=state.feed_ph,
        drain_ph=state.drain_ph,
        drainage_ratio=state.drainage_ratio,
        outside_temp=state.outside_temp,
        outside_humidity=state.outside_humidity,
        growth_stage=growth_stage,
        time_of_day=state.time_of_day,
        sensor_quality=state.sensor_quality,
        missing_fields=missing_fields,
        fallback_fields=state.fallback_fields,
        suspicious_fields=state.suspicious_fields,
        assumed_units=state.assumed_units,
        stale_timestamp=state.stale_timestamp,
        source_labels=state.source_labels,
        quality_warnings=warnings,
    )
