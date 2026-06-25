# BerryNext Threshold / Literature Rule Engine

BerryNext uses `config/evidence_rules.json` as the central evidence table for rule-based recommendation support.
The table is not a validated agronomic prescription database. It is a structured, traceable rule catalog for the prototype decision-support pipeline.

```text
Sensor Data
-> Current State Builder
-> Environmental Predictor
-> Scenario Simulator
-> Threshold / Literature Rule Engine
-> Work-Need Scorer
-> Recommendation Generator
```

## Rule Schema

Each rule entry includes:

- `rule_id` / `id`: stable rule reference
- `action_type`: recommendation module or auxiliary alert module
- `rule_category`: `level1_core_action`, `level1_supporting_rule`, or `level2_auxiliary_alert`
- `variable`: primary variable for the rule
- `condition`: normalized condition summary
- `threshold`: threshold or range text
- `unit`: unit assumptions
- `growth_stage_scope`: optional stage scope
- `source_type`: `literature`, `manual`, `agronomic_assumption`, or `prototype`
- `source_note`: provenance and review note
- `confidence_level`: `low`, `medium`, or `high`
- `needs_local_calibration`: whether the rule must be calibrated locally before stronger claims
- `recommendation_effect`: how the rule affects work-need or alert priority
- `risk_note`: caution shown to keep output in decision-support mode

Legacy fields such as `condition_variables`, `condition_description`, `threshold_or_range`, `expected_effect`, `risk_or_caution`, and `evidence_level` remain for compatibility with existing recommendation modules and scenario outputs.

## Level 1 Core Actions

The default core rule set is limited to:

- `irrigation`
- `nutrient_ec_check`
- `ventilation_dehumidification`
- `shading_high_temperature`
- `heating_low_temperature`

`ph_check` is kept as a supporting rule for EC / nutrient solution adjustment. It should not be presented as a sixth Level 1 action.

## Level 2 Auxiliary Alerts

These rules are auxiliary alerts and should not be ranked as core Level 1 management actions by default:

- `disease_environment_risk_proxy`
- `harvest_monitoring`
- `leaf_removal_caution`

Disease rules are environmental scouting proxies only. Harvest and leaf-removal rules are review alerts only unless explicit local outcome labels, validation results, and tests are added.

## Calibration Policy

Prototype or manual-review-needed thresholds are explicitly marked with `source_type="prototype"` or with a manual-review source note. They keep `needs_local_calibration=true` and `confidence_level="low"` unless a stronger citation and local validation justify a change.

Current thresholds that still need literature review or local calibration include:

- substrate moisture and cumulative-radiation irrigation triggers
- EC target ranges by cultivar, substrate, season, and growth stage
- humidity/VPD ventilation triggers
- high-temperature/radiation shading triggers
- low-temperature heating and heat-preservation triggers
- disease-risk, harvest, and leaf-removal auxiliary alert cutoffs
