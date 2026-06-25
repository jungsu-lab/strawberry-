# BerryNext Work-Need Scorer

`WorkNeedScorer` converts current state, gated environmental predictions, and evidence rules into explainable 0-100 work-need scores for the five Level 1 greenhouse management actions.

```text
Sensor Data
-> Current State Builder
-> Environmental Predictor
-> Scenario Simulator
-> Threshold / Literature Rule Engine
-> Work-Need Scorer
-> Recommendation Generator
```

## Level 1 Scores

The scorer returns one `WorkNeedScore` for each core action:

- `irrigation`
- `nutrient_ec_check`
- `ventilation_dehumidification`
- `shading_high_temperature`
- `heating_low_temperature`

Auxiliary alerts such as disease scouting, harvest possibility, and leaf-removal review are not included in the default Level 1 score set.

## Components

Each score exposes the same component fields:

- `moisture_stress`
- `salinity_stress`
- `high_temp_stress`
- `low_temp_stress`
- `disease_environment_risk`
- `energy_cost`

The components are prototype decision-support signals. They are not validated agronomic truth or autonomous control values.

## Status

`WorkNeedScore.status` is derived from the 0-100 score:

- `recommend`: 70 or above
- `caution`: 55 to below 70
- `hold`: 30 to below 55
- `monitor`: below 30

All scores require human review.

## Prediction Use

Rules and current state remain primary. Predictions can raise scores only when they pass the existing confidence gate. Low-confidence or fallback predictions do not create high-priority scores by themselves.

Work history is not used as a supervised label. Future integration may use work history only for cooldown, safety spacing, or explanation.

## Limitations

The current thresholds are provisional literature/manual/prototype assumptions from `config/evidence_rules.json`. They require local calibration by cultivar, substrate, sensor units, season, growth stage, and farm operating strategy.
