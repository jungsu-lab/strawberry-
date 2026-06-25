# BerryNext Environmental Predictor

The Environmental Predictor produces short-term environmental delta predictions for the decision-support pipeline.
It predicts greenhouse state variables, not farmwork actions.

```text
Sensor Data
-> Current State Builder
-> Environmental Predictor
-> Scenario Simulator
-> Threshold / Literature Rule Engine
-> Work-Need Scorer
-> Recommendation Generator
```

## Targets

Baseline predictors currently support these normalized `CurrentGreenhouseState` fields:

- `air_temp`
- `humidity`
- `vpd`
- `solar_radiation`
- `root_zone_moisture`
- `drain_ec`

Each `PredictionResult` includes:

- `target`
- `horizon_hours`
- `current_value`
- `predicted_delta`
- `predicted_value`
- `confidence`
- `model_used`
- `fallback_used`
- `fallback_reason`

## Predictors

| Version | Class | Behavior |
| --- | --- | --- |
| v0 | `NoChangeBaselinePredictor` | Returns `predicted_delta = 0` and `predicted_value = current_value`. Uses conservative confidence and marks `fallback_used = true`. |
| v1 | `RollingDeltaBaselinePredictor` | Estimates recent per-hour delta from available history. Falls back to v0 behavior when history or target history is unavailable. |
| v3 placeholder | `GAMReadyPredictor` | Exists only as an integration placeholder and raises `NotImplementedError`. |

`predict_environment_delta(...)` uses `RollingDeltaBaselinePredictor` by default and returns offline predictions for horizons 1, 2, and 3 unless other horizons are supplied.

## Why Baselines Exist

The baselines let the downstream scenario simulator, rule scorer, and recommendation generator be tested without claiming that GAM or another trained model exists. They provide stable `PredictionResult` objects while keeping confidence conservative and fallback status explicit.

## GAM Status

GAM is planned for future short-term environmental delta prediction. No GAM training, GAM validation metrics, or GAM-backed recommendations are implemented in this module.
