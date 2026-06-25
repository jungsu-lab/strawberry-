# BerryNext Scenario Simulation

Scenario simulation compares candidate greenhouse management actions for the next 1 to 3 hours.
It is decision support for human review.

It must not be used to fabricate farmwork labels for supervised training.
It must not be presented as ground-truth physical simulation or autonomous control.

```text
Sensor Data
-> Current State Builder
-> Environmental Predictor
-> Scenario Simulator
-> Threshold / Literature Rule Engine
-> Work-Need Scorer
-> Recommendation Generator
```

## Candidate Actions

`compare_action_candidates(...)` supports the Level 1 action candidates and no-action alternatives:

- `irrigation`
- `no_irrigation`
- `lower_ec_nutrient_adjustment`
- `raise_ec_check_supplied_ec`
- `ventilation`
- `no_ventilation`
- `shading`
- `no_shading`
- `heat_preservation_heating_review`
- `no_heat_preservation`

Disease, harvest, and leaf-removal remain Level 2 auxiliary alerts. They are not included as core short-horizon action candidates unless validated data and tests are added.

## Output

Each `ShortHorizonScenarioResult` is machine-readable and includes:

- moisture delta
- EC delta
- salinity-stress delta
- humidity delta
- VPD delta
- temperature delta
- disease-environment-risk proxy delta
- energy-cost delta
- confidence
- warnings
- evidence rule ids or tags
- expected benefits and risks

Every result has `is_training_label=False` and `model_status="heuristic_prototype"`.

## Limitations

The current short-horizon comparison is heuristic. It is useful for pipeline testing, explanation, and candidate comparison, but it is not a calibrated physics model. Local validation is required before using numeric effect sizes operationally.
