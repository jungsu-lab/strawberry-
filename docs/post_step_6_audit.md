# Post Step 6 Integration Audit

Audit date: 2026-06-25

## Scope

Reviewed the implemented pieces for steps 1 to 6:

1. data contract
2. evidence rules
3. GAM notebook/script handoff
4. model confidence gate
5. action-specific recommendation modules
6. v0 what-if scenario simulator

## What Works

- `GreenhouseSnapshot` and related state models load from `examples/sample_decision_contract.json` through `libsbapi/decision_contract_io.py`.
- `config/evidence_rules.json` loads through `load_evidence_rules()` and groups by action type.
- `ActionRecommendationEngine` aggregates action-specific recommendation modules and returns `RecommendationResult` values.
- Optional `PredictionResult` inputs now pass through action-specific target matching and the model confidence gate before recommendations are returned.
- Weak or incomplete prediction metrics fall back to `model_used="literature_manual_rules"` with `fallback_used=true` and explicit safety flags.
- `libsbapi/scenario_simulator.py` compares directional what-if scenarios.
- `scripts/run_scenario_simulation.py` runs with `examples/sample_scenario_simulation_input.json` and writes `examples/sample_scenario_simulation_output.json`.
- The end-to-end test `tests/test_post_step_6_integration.py` loads sample data, evidence rules, recommendation modules, confidence gate behavior, and scenario simulation in one path.

## Broken And Fixed

- Disease risk action naming was inconsistent. The public action category is now `disease_environment_risk_proxy`, not `disease_environment_risk_monitoring`.
- `ActionRecommendationEngine` accepted optional predictions but did not apply the confidence gate. It now applies action-specific target matching, `gate_prediction_result()`, and `apply_prediction_gate_to_recommendation()` when predictions are supplied.
- The end-to-end test now verifies that weak prediction metrics fall back to rule-based recommendations and expose `reason`, `risks`, `evidence_references`, `confidence`, `fallback_used`, and `safety_flags`.

## Still Assumption-Based

- The evidence table is literature/manual-based and marked for local calibration.
- Disease output is only an environmental risk proxy. The system does not predict actual disease without labeled disease observations.
- The v0 scenario simulator is directional only. It is not a validated causal simulator and does not issue greenhouse control commands.
- Leaf removal remains conservative because excessive defoliation can reduce plant vigor.
- Scenario confidence is heuristic and should not be interpreted as validated probability.

## GAM Status

The repository still does not contain a runnable GAM training/evaluation script. The audit found external artifacts:

- `/home/jungsu0327/notebookaaa758c805 (1).ipynb`
- `/home/jungsu0327/gam_outputs/strawberry_gam_model_summary.csv`
- `/home/jungsu0327/gam_outputs/strawberry_gam_decision_table.csv`

In-repository GAM integration currently consists of:

- `PredictionResult`
- sample prediction JSON
- `libsbapi/prediction_confidence.py`
- tests for confidence gate fallback behavior

Do not claim repository-integrated GAM training until the notebook logic is moved into a versioned script with tests and declared dependencies.

## Verification

Commands run during this audit:

```bash
python3 -m unittest discover
python3 scripts/run_scenario_simulation.py examples/sample_scenario_simulation_input.json examples/sample_scenario_simulation_output.json
python3 -m unittest tests.test_post_step_6_integration
```

Result: all tests passed, including the new end-to-end test.

## Recommended Next Steps

1. Move the GAM notebook workflow into a repository script such as `scripts/train_gam_predictions.py`.
2. Define a stable prediction artifact format that writes `PredictionResult`-compatible metrics, especially `validation_mae`, `baseline_mae`, `validation_r2`, `training_rows`, and `missing_feature_ratio`.
3. Add tests that load a sample GAM metric artifact and prove weak models cannot affect recommendation priority.
4. Add an integration example that runs recommendation generation and scenario simulation from the same sample input file.
5. Add local calibration configuration for thresholds before adding any economic scoring.
