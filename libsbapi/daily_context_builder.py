from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

from .berrynext import GreenhouseSnapshot, ImageGrowthSignals, WeatherForecast
from .farmwork import (
    CropGrowthStage,
    FarmWorkContext,
    FarmWorkHistory,
)
from .xlsx_reader import read_xlsx_records

DATE_RE: Final = re.compile(r"^\d{4}-\d{2}-\d{2}")
DEFAULT_FARMS: Final = ("electric", "pellet")


@dataclass(frozen=True, slots=True)
class DailyContextRecord:
    farm_id: str
    day: date
    context: FarmWorkContext
    source_files: tuple[str, ...]

    def output_name(self) -> str:
        return f"{self.farm_id}_{self.day.isoformat()}.json"


@dataclass(frozen=True, slots=True)
class EnvDaily:
    day: date
    inside_temperature_c: float | None
    inside_humidity_pct: float | None
    co2_ppm: float | None
    solar_radiation_w_m2: float | None
    root_zone_moisture_pct: float | None
    ec: float | None
    ph: float | None
    rain_probability: float | None


@dataclass(frozen=True, slots=True)
class ControlDaily:
    day: date
    vent_open_pct: float | None


@dataclass(frozen=True, slots=True)
class GrowthSample:
    day: date
    week: int | None
    leaf_count: float | None
    leaf_length_mm: float | None
    leaf_width_mm: float | None
    fruit_count: int | None


def build_daily_context_records(core_dir: Path) -> list[DailyContextRecord]:
    records: list[DailyContextRecord] = []
    for farm_id in DEFAULT_FARMS:
        farm_dir = core_dir / farm_id
        if not farm_dir.exists():
            continue
        records.extend(_build_farm_records(farm_id, farm_dir))
    return sorted(records, key=lambda item: (item.farm_id, item.day))


def _build_farm_records(farm_id: str, farm_dir: Path) -> list[DailyContextRecord]:
    env_path = farm_dir / "env_hourly.xlsx"
    control_path = farm_dir / "control_hourly.xlsx"
    growth_path = farm_dir / "growth.xlsx"
    env_by_day = _env_daily(env_path)
    control_by_day = _control_daily(control_path)
    growth_samples = _growth_samples(growth_path)

    records: list[DailyContextRecord] = []
    for day, env in env_by_day.items():
        growth = _latest_growth_sample(growth_samples, day)
        control = control_by_day.get(day)
        context = FarmWorkContext(
            growth_stage=_growth_stage(growth),
            snapshot=_snapshot(env, control, growth),
            history=_history(growth, day),
        )
        records.append(
            DailyContextRecord(
                farm_id=farm_id,
                day=day,
                context=context,
                source_files=(str(env_path), str(control_path), str(growth_path)),
            )
        )
    return records


def _env_daily(path: Path) -> dict[date, EnvDaily]:
    buckets: dict[date, list[dict[str, str]]] = {}
    for row in read_xlsx_records(path):
        row_date = _date_from_text(row.get("수집일", ""))
        if row_date is None:
            continue
        buckets.setdefault(row_date, []).append(row)

    result: dict[date, EnvDaily] = {}
    for day, rows in buckets.items():
        result[day] = EnvDaily(
            day=day,
            inside_temperature_c=_mean(rows, ("내부-내부온도",)),
            inside_humidity_pct=_mean(rows, ("내부-내부습도",)),
            co2_ppm=_mean(rows, ("내부-내부CO2",)),
            solar_radiation_w_m2=_mean_preferred(rows, ("내부-내부일사량", "외부-외부일사량")),
            root_zone_moisture_pct=_mean_positive(rows, ("토양-지습", "양액-지습")),
            ec=_mean_positive(rows, ("양액-(양액)배액EC", "토양-토양EC")),
            ph=_mean_positive(rows, ("양액-(양액)배액PH", "토양-토양PH")),
            rain_probability=_rain_probability(rows),
        )
    return result


def _control_daily(path: Path) -> dict[date, ControlDaily]:
    buckets: dict[date, list[dict[str, str]]] = {}
    for row in read_xlsx_records(path):
        row_date = _date_from_text(row.get("수집일", ""))
        if row_date is None:
            continue
        buckets.setdefault(row_date, []).append(row)

    result: dict[date, ControlDaily] = {}
    for day, rows in buckets.items():
        vent_columns = tuple(header for header in rows[0] if "개도율" in header)
        result[day] = ControlDaily(day=day, vent_open_pct=_mean_all(rows, vent_columns))
    return result


def _growth_samples(path: Path) -> list[GrowthSample]:
    samples: list[GrowthSample] = []
    for row in read_xlsx_records(path):
        row_date = _date_from_text(row.get("조사일", ""))
        if row_date is None:
            continue
        fruit_values = [
            _float_or_none(row.get("화방착과수1(개)", "")),
            _float_or_none(row.get("화방착과수2(개)", "")),
            _float_or_none(row.get("화방착과수3(개)", "")),
        ]
        fruit_count = round(sum(value for value in fruit_values if value is not None))
        samples.append(
            GrowthSample(
                day=row_date,
                week=_int_or_none(row.get("주차", "")),
                leaf_count=_float_or_none(row.get("엽수(개)", "")),
                leaf_length_mm=_float_or_none(row.get("엽장(mm)", "")),
                leaf_width_mm=_float_or_none(row.get("엽폭(mm)", "")),
                fruit_count=fruit_count,
            )
        )
    return sorted(samples, key=lambda item: item.day)


def _snapshot(
    env: EnvDaily,
    control: ControlDaily | None,
    growth: GrowthSample | None,
) -> GreenhouseSnapshot:
    leaf_density = None
    if growth is not None and growth.leaf_count is not None:
        leaf_density = min(1.0, growth.leaf_count / 8.0)

    return GreenhouseSnapshot(
        inside_temperature_c=env.inside_temperature_c,
        inside_humidity_pct=env.inside_humidity_pct,
        co2_ppm=env.co2_ppm,
        solar_radiation_w_m2=env.solar_radiation_w_m2,
        root_zone_moisture_pct=env.root_zone_moisture_pct,
        ec=env.ec,
        ph=env.ph,
        vent_open_pct=control.vent_open_pct if control is not None else None,
        weather=WeatherForecast(rain_probability=env.rain_probability),
        image=ImageGrowthSignals(
            fruit_count=growth.fruit_count if growth is not None else None,
            leaf_density=leaf_density,
        ),
    )


def _history(growth: GrowthSample | None, day: date) -> FarmWorkHistory:
    return FarmWorkHistory(
        days_since_scouting=(day - growth.day).days if growth is not None else None,
    )


def _growth_stage(growth: GrowthSample | None) -> CropGrowthStage:
    if growth is None or growth.week is None:
        return CropGrowthStage.VEGETATIVE
    if growth.fruit_count is not None and growth.fruit_count >= 10:
        return CropGrowthStage.HARVEST
    if growth.fruit_count is not None and growth.fruit_count > 0:
        return CropGrowthStage.FRUITING
    if growth.week >= 10:
        return CropGrowthStage.FLOWERING
    return CropGrowthStage.VEGETATIVE


def _latest_growth_sample(samples: list[GrowthSample], target_day: date) -> GrowthSample | None:
    latest = None
    for sample in samples:
        if sample.day > target_day:
            break
        latest = sample
    return latest


def _date_from_text(value: str) -> date | None:
    match = DATE_RE.match(value.strip())
    if match is None:
        return None
    return date.fromisoformat(match.group(0))


def _mean(rows: list[dict[str, str]], columns: tuple[str, ...]) -> float | None:
    values = _values(rows, columns, positive_only=False)
    return sum(values) / len(values) if values else None


def _mean_positive(rows: list[dict[str, str]], columns: tuple[str, ...]) -> float | None:
    values = _values(rows, columns, positive_only=True)
    return sum(values) / len(values) if values else None


def _mean_preferred(rows: list[dict[str, str]], columns: tuple[str, ...]) -> float | None:
    fallback = None
    for column in columns:
        values = [_float_or_none(row.get(column, "")) for row in rows]
        numeric_values = [value for value in values if value is not None]
        if not numeric_values:
            continue
        candidate = sum(numeric_values) / len(numeric_values)
        fallback = candidate if fallback is None else fallback
        if any(value > 0 for value in numeric_values):
            return candidate
    return fallback


def _mean_all(rows: list[dict[str, str]], columns: tuple[str, ...]) -> float | None:
    values: list[float] = []
    for row in rows:
        for column in columns:
            value = _float_or_none(row.get(column, ""))
            if value is not None:
                values.append(value)
    return sum(values) / len(values) if values else None


def _values(rows: list[dict[str, str]], columns: tuple[str, ...], positive_only: bool) -> list[float]:
    values: list[float] = []
    for row in rows:
        for column in columns:
            value = _float_or_none(row.get(column, ""))
            if value is None:
                continue
            if positive_only and value <= 0:
                continue
            values.append(value)
            break
    return values


def _rain_probability(rows: list[dict[str, str]]) -> float | None:
    values = _values(rows, ("외부-강우감지",), positive_only=False)
    if not values:
        return None
    rainy_hours = sum(1 for value in values if value > 0)
    return round(rainy_hours / len(values) * 100.0, 1)


def _float_or_none(value: str) -> float | None:
    cleaned = value.strip().replace(",", "")
    if cleaned in {"", "-"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _int_or_none(value: str) -> int | None:
    parsed = _float_or_none(value)
    return round(parsed) if parsed is not None else None
