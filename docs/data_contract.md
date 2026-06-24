# Decision Data Contract

This project recommends strawberry farm work actions. It does not directly control greenhouse equipment.

The stable internal contract lives in:

- `libsbapi/decision_contract.py`: frozen dataclass models and basic range validation.
- `libsbapi/decision_contract_io.py`: JSON loading helpers for sample or boundary data.
- `libsbapi/prediction_confidence.py`: model confidence gates and recommendation fallback helpers.
- `libsbapi/action_recommenders/`: action-specific recommendation modules and aggregator.
- `libsbapi/scenario_simulator.py`: v0 what-if scenario estimates for action candidates.
- `examples/sample_decision_contract.json`: example input/output bundle.

## Core Models

`GreenhouseSnapshot` is the current state passed into decision logic. It groups:

- `SensorState`: temperature, humidity, VPD, radiation, cumulative radiation, CO2.
- `RootZoneState`: substrate moisture, root-zone EC, root-zone pH.
- `NutrientState`: drainage EC/pH, feed EC/pH, drainage ratio.
- `WeatherState`: rain probability, expected rain, outside temperature/humidity.
- `GrowthState`: growth stage, fruit count, ripe fruit ratio, leaf density, disease spot proxy.
- `WorkHistoryEvent`: recent farm work logs such as irrigation, harvest, scouting, or leaf pruning.

`PredictionResult` records model outputs without making them authoritative. It includes target, horizon, predicted value or delta, confidence, model name, fallback flag, and optional metrics.

`RecommendationResult` is the final decision-support output. Required fields include:

- `action_type`
- `priority`
- `confidence`
- `reason`
- `expected_effect`
- `risks`
- `evidence_references`
- `safety_flags`
- `model_used`
- `fallback_used`

## Safety Semantics

Every recommendation should be treated as decision support. Use `safety_flags` such as:

- `decision_support_only`
- `requires_human_review`
- `low_model_confidence`
- `missing_sensor_data`

GAM or other ML predictions should only adjust recommendations when their confidence and data quality are acceptable. If not, set `fallback_used=true` and explain the rule-based fallback in `reason`, `risks`, or `safety_flags`. See `docs/model_confidence_gates.md` for the current gate statuses and metric requirements.

## JSON Sample

Load the sample contract with:

```python
from pathlib import Path

from libsbapi.decision_contract_io import load_decision_contract_sample

sample = load_decision_contract_sample(Path("examples/sample_decision_contract.json"))
print(sample.recommendation.action_type)
```

This JSON shape is intended as a boundary format for notebooks, scripts, and future GAM prediction modules. Existing `berrynext.py` and `farmwork.py` rule engines can continue to use their current classes until they are adapted to this contract.

For the modular action pipeline, see `docs/action_recommendations.md`.

For v0 what-if action comparison, see `docs/scenario_simulator.md`.
