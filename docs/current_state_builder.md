# BerryNext Current State Builder

`CurrentStateBuilder` normalizes legacy daily-context JSON, `FarmWorkContext`, and greenhouse snapshot objects into `CurrentGreenhouseState`.

It is the pipeline step between raw sensor data and prediction/scoring:

```text
Sensor Data
-> Current State Builder
-> Environmental Predictor
-> Scenario Simulator
-> Threshold / Literature Rule Engine
-> Work-Need Scorer
-> Recommendation Generator
```

## Inputs

- `CurrentStateBuilder.from_daily_context_file(path)`
- `CurrentStateBuilder.from_daily_context(payload, source_label="daily_context")`
- `CurrentStateBuilder.from_farmwork_context(context)`
- `CurrentStateBuilder.from_greenhouse_snapshot(snapshot)`

The builder accepts both legacy keys such as `inside_temperature_c`, `inside_humidity_pct`, `root_zone_moisture_pct`, `ec`, and `ph`, and newer normalized names such as `air_temp`, `humidity`, `root_ec`, `drain_ec`, and `drain_ph`.

## Normalized Fields

Core state fields:

- `air_temp`
- `humidity`
- `vpd`
- `co2`
- `solar_radiation`
- `cumulative_solar_radiation`
- `substrate_moisture`
- `root_zone_moisture`
- `feed_ec`
- `drain_ec`
- `root_ec`
- `feed_ph`
- `drain_ph`
- `drainage_ratio`
- `outside_temp`
- `outside_humidity`
- `growth_stage`
- `time_of_day`
- `timestamp`

If `vpd` is missing but air temperature and humidity are present, the builder calculates VPD with the existing BerryNext VPD helper and records `vpd` in `fallback_fields`.

## Quality Metadata

The builder does not invent missing values. Missing values remain `None` and are exposed through:

- `missing_fields`
- `quality_warnings`

Additional metadata:

- `assumed_units`: unit assumptions used while normalizing legacy fields
- `source_labels`: source names such as `sample_daily_context`, `farmwork_context`, or a custom label
- `stale_timestamp`: `True` or `False` only when a parseable timestamp exists, otherwise `None`
- `fallback_fields`: fields calculated from other observed fields
- `suspicious_fields`: ambiguous zero-valued sensor fields that should be checked
- `sensor_quality`: optional source-provided sensor-quality metadata

Zero values are preserved. Ambiguous zero values are flagged rather than discarded.
