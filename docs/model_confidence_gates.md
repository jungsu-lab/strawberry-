# Model Confidence Gates

The strawberry decision system is decision support, not an autonomous controller. GAM or other ML predictions can only adjust recommendation priority when they pass explicit confidence gates.

## Why Gates Exist

The project may have limited local training data, missing targets, or weak validation results. A prediction that does not beat a simple baseline should not make irrigation, EC, ventilation, shading, or heating recommendations more urgent.

Predictions are also action-specific. A `substrate_moisture_pct` prediction can support irrigation decisions, but it must not make EC, disease-proxy, harvest, or leaf-removal recommendations appear model-driven.

When a model fails a gate, the recommendation must fall back to literature/manual rules and expose that fallback through:

- `RecommendationResult.model_used`
- `RecommendationResult.fallback_used`
- `RecommendationResult.confidence`
- `RecommendationResult.safety_flags`
- `RecommendationResult.risks`

## Gate Checks

The gate implemented in `libsbapi/prediction_confidence.py` checks:

- minimum usable training rows
- target availability
- validation MAE compared with baseline MAE
- validation R2, when available
- missing feature ratio

The expected metrics can be supplied in `PredictionResult.metrics` with keys such as:

- `training_rows` or `usable_training_rows`
- `validation_mae`
- `baseline_mae`
- `validation_r2`
- `missing_feature_ratio`

## Status Values

- `usable_model`: the model has enough data and beats the baseline, so it may influence recommendation priority.
- `weak_model_fallback`: validation metrics are missing, worse than baseline, or R2 is below the configured minimum.
- `insufficient_data_fallback`: usable rows are too low or feature missingness is too high.
- `missing_target_fallback`: the target is missing or unavailable.

## Interpretation

Fallback does not mean no work is needed. It means the system should rely on literature/manual thresholds, local safety constraints, and human review instead of using the GAM prediction to raise or lower priority.

These gates protect the presentation claim: the system combines model-assisted short-term state prediction with rule-based decision support, but weak or unvalidated models do not drive final recommendations.

The v0 what-if simulator uses the same gate. Weak, missing, or unrelated predictions can be reported as assumptions for traceability, but they do not increase scenario confidence.
