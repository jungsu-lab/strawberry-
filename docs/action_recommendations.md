# Action Recommendation Modules

The contract-based recommendation pipeline lives under `libsbapi/action_recommenders/`.

It is separate from the older `BerryNextDecisionEngine` and `DailyFarmWorkDecisionEngine` MVP classes. The new pipeline returns `RecommendationResult` objects and uses the structured evidence table from `config/evidence_rules.json`.

## Modules

Each action category has its own module. The first five modules are Level 1 greenhouse management actions; the last three are Level 2 auxiliary alerts.

Level 1 actions:

- `irrigation`
- `nutrient_ec_check`
- `ventilation_dehumidification`
- `shading_high_temperature`
- `heating_low_temperature`

`ph_check` remains a supporting EC / nutrient-solution review module. It is not displayed as a sixth Level 1 action.

Level 2 auxiliary alerts:

- `disease_environment_risk_proxy`
- `harvest_monitoring`
- `leaf_removal_caution`

Each module accepts a `RecommendationContext` containing:

- `GreenhouseSnapshot`
- recent `WorkHistoryEvent` entries used only for safety spacing, cooldown intervals, or explanation
- matching `EvidenceRule` entries
- optional `PredictionResult` values

Each module returns one or more `RecommendationResult` objects. The baseline rules are conservative literature/manual assumptions and use `model_used="literature_manual_rules"` with `fallback_used=true`.

When predictions are supplied, `ActionRecommendationEngine` first matches each `PredictionResult.target` to relevant action types. A usable prediction that passes the confidence gate can adjust that action module's score and reason. Weak, missing, or unrelated predictions remain explicit fallbacks and must not make unrelated actions appear model-driven.

GAM is planned as an environmental delta predictor, not as a direct task classifier. The expected predictor progression is v0 no-change baseline, v1 rolling delta baseline, v2 linear regression, v3 GAM, and v4 LSTM or Transformer only if enough data and validation support it.

## Aggregator

Use `ActionRecommendationEngine.recommend()` for the ranked Level 1 greenhouse management list. It returns only the five core actions:

```python
from libsbapi.action_recommenders import ActionRecommendationEngine
from libsbapi.evidence_rules import load_evidence_rules

engine = ActionRecommendationEngine(load_evidence_rules())
level1_recommendations = engine.recommend(snapshot)
auxiliary_alerts = engine.auxiliary_alerts(snapshot)
```

Multiple predictions can be supplied together:

```python
level1_recommendations = engine.recommend(snapshot, prediction=predictions)
auxiliary_alerts = engine.auxiliary_alerts(snapshot, prediction=predictions)
```

Auxiliary alerts are filtered separately and should be shown under `보조 알림` or `Auxiliary Alerts`. They may reference a Level 1 action to check first, for example high humidity and low VPD can produce a ventilation recommendation in the Level 1 list and an environmental disease-risk scouting alert in the auxiliary list.

## Safety Notes

These recommendations do not issue greenhouse control commands. They are decision-support outputs for human review.

Disease, harvest, and leaf-removal modules are Level 2 auxiliary alerts. They should not be displayed as core greenhouse management actions or ranked above the five Level 1 actions by default.

Disease recommendations are environmental disease-risk proxies only. They are not actual disease predictions unless locally labeled disease data is added and validated.

Harvest recommendations are harvest possibility alerts only. They are not validated harvest timing predictions unless explicit harvest outcome data and tests are added.

Leaf removal remains cautious by design. Dense canopy or high humidity can raise monitoring priority, but the module avoids aggressive recommendations because excessive defoliation can reduce plant vigor and yield potential.

Scenario simulation compares action candidates for explanation. It must not be used to fabricate work-history labels or supervised-training targets.
