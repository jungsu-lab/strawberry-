# BerryNext Recommendation Generator

The Recommendation Generator is the final stage of the BerryNext decision-support pipeline.

```text
Sensor Data
-> Current State Builder
-> Environmental Predictor
-> Scenario Simulator
-> Threshold / Literature Rule Engine
-> Work-Need Scorer
-> Recommendation Generator
```

## Role

The generator turns `WorkNeedScore` objects, prediction references, scenario comparison notes, and evidence rule IDs into human-readable and JSON-like recommendation output.

It does not issue actuator commands and does not claim autonomous greenhouse control.

## Level 1 Output

The main ranked list contains only the five greenhouse management actions:

- `irrigation`
- `nutrient_ec_check`
- `ventilation_dehumidification`
- `shading_high_temperature`
- `heating_low_temperature`

Each recommendation includes:

- action name
- 0-100 score
- status: `recommend`, `caution`, `hold`, or `monitor`
- reasons
- expected effects
- risks or warnings
- evidence rule IDs
- prediction references
- scenario comparison references
- `mode="decision_support"`
- `requires_human_review=true`

## Level 2 Auxiliary Alerts

Auxiliary alerts are shown separately from the ranked Level 1 list:

- `disease_environment_risk_proxy`
- `harvest_monitoring`
- `leaf_removal_caution`

These are scouting or review alerts only. They are not validated disease, harvest, or leaf-removal prediction systems unless explicit local data, validation metrics, and tests are added.

## Current Demo

`examples/berrynext_today_recommendation.py` builds the final offline report from `examples/sample_daily_context.json`.

The current predictor is a baseline/fallback predictor. GAM remains a future Environmental Predictor implementation and is not claimed as implemented.
