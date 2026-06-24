# Evidence Rules

The structured evidence table lives at:

```text
config/evidence_rules.json
```

The loader lives at:

```python
from libsbapi.evidence_rules import load_evidence_rules, evidence_rules_by_action_type
```

## Purpose

The evidence table stores literature/manual assumptions used to explain farm-work recommendations. It is not a table of locally validated causal effects, and it is not a trained model.

Each entry includes:

- `id`
- `action_type`
- `condition_variables`
- `condition_description`
- `threshold_or_range`
- `expected_effect`
- `risk_or_caution`
- `evidence_level`
- `source_title`
- `source_note`
- `needs_local_calibration`

## Action Categories

The current table covers:

- `irrigation`
- `nutrient_ec_check`
- `ph_check`
- `ventilation_dehumidification`
- `shading_high_temperature`
- `heating_low_temperature`
- `disease_environment_risk_proxy`
- `harvest_monitoring`
- `leaf_removal_caution`

## Modeling Cautions

Disease-related rules must be described as environmental disease-risk proxy monitoring unless real disease labels are available. High humidity, low VPD, rain, leaf wetness, or image/scouting proxy signals can justify scouting priority, but they do not prove actual disease incidence.

Leaf-removal rules are conservative. Dense canopy and old/diseased leaves may justify review, but excessive leaf removal can reduce photosynthetic area, plant vigor, and yield potential.

All thresholds are starting assumptions. Every entry has `needs_local_calibration=true` because cultivar, substrate, sensor units, greenhouse design, season, and farm management targets can change safe operating ranges.

## How Decision Logic Should Use It

Decision logic should load rules once and attach matching evidence entries to recommendations by `action_type`. Thresholds and source notes should be read from the table where practical instead of being repeated as free text inside scoring functions.

GAM or other ML outputs should be reported separately as `PredictionResult` values. If a recommendation uses both a model and the evidence table, the output should state which part came from model prediction and which part came from literature/manual assumptions.
