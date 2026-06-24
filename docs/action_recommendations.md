# Action Recommendation Modules

The contract-based recommendation pipeline lives under `libsbapi/action_recommenders/`.

It is separate from the older `BerryNextDecisionEngine` and `DailyFarmWorkDecisionEngine` MVP classes. The new pipeline returns `RecommendationResult` objects and uses the structured evidence table from `config/evidence_rules.json`.

## Modules

Each action category has its own module:

- `irrigation`
- `nutrient_ec_check`
- `ph_check`
- `ventilation_dehumidification`
- `shading_high_temperature`
- `heating_low_temperature`
- `disease_environment_risk_proxy`
- `harvest_monitoring`
- `leaf_removal_caution`

Each module accepts a `RecommendationContext` containing:

- `GreenhouseSnapshot`
- recent `WorkHistoryEvent` entries
- matching `EvidenceRule` entries
- optional `PredictionResult` values

Each module returns one or more `RecommendationResult` objects. The baseline rules are conservative literature/manual assumptions and use `model_used="literature_manual_rules"` with `fallback_used=true`.

When predictions are supplied, `ActionRecommendationEngine` first matches each `PredictionResult.target` to relevant action types. A usable prediction that passes the confidence gate can adjust that action module's score and reason. Weak, missing, or unrelated predictions remain explicit fallbacks and must not make unrelated actions appear model-driven.

## Aggregator

Use `ActionRecommendationEngine` to aggregate all action modules:

```python
from libsbapi.action_recommenders import ActionRecommendationEngine
from libsbapi.evidence_rules import load_evidence_rules

engine = ActionRecommendationEngine(load_evidence_rules())
recommendations = engine.recommend(snapshot)
```

Multiple predictions can be supplied together:

```python
recommendations = engine.recommend(snapshot, prediction=predictions)
```

## Safety Notes

These recommendations do not issue greenhouse control commands. They are decision-support outputs for human review.

Disease recommendations are environmental disease-risk proxies only. They are not actual disease predictions unless locally labeled disease data is added and validated.

Leaf removal remains cautious by design. Dense canopy or high humidity can raise monitoring priority, but the module avoids aggressive recommendations because excessive defoliation can reduce plant vigor and yield potential.
