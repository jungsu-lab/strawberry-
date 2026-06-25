# BerryNext Functional Trustworthiness Audit

Date: 2026-06-25
Branch: `feature/greenhouse-dashboard`
Mode: audit only. No production code was modified for this audit.

## Executive Answer

BerryNext is functionally trustworthy as a transparent offline decision-support prototype, but not yet trustworthy as an operational greenhouse decision system.

The repository now contains the corrected architecture, offline examples, tests, Level 1 / Level 2 separation, baseline prediction contracts, scenario comparison, rule metadata, scoring, and recommendation output. The main remaining reliability issues are state-flow consistency, generic confidence scoring, scenario-to-score integration, and prototype threshold calibration.

## Files Inspected

- `AGENT_MEMORY.md`
- `README.md`, `BERRYNEXT_AI_PLAN.md`, `DESIGN.md`
- `docs/`
- `config/evidence_rules.json`
- `examples/sample_daily_context.json`
- `examples/berrynext_today_recommendation.py`
- `examples/greenhouse_scenario_compare.py`
- `dashboard/greenhouse_dashboard.py`
- `libsbapi/current_state_builder.py`
- `libsbapi/decision_contract.py`
- `libsbapi/environmental_prediction.py`
- `libsbapi/evidence_rules.py`
- `libsbapi/work_need_scorer.py`
- `libsbapi/recommendation_generator.py`
- `libsbapi/scenario_comparison.py`
- `libsbapi/offline_demo.py`
- `libsbapi/auxiliary_alert_scoring.py`
- `libsbapi/display_labels.py`
- `libsbapi/action_recommenders/`
- `tests/test_current_state_builder.py`
- `tests/test_environmental_prediction.py`
- `tests/test_evidence_rules.py`
- `tests/test_work_need_scorer.py`
- `tests/test_recommendation_generator.py`
- `tests/test_short_horizon_scenario_comparison.py`
- `tests/test_greenhouse_dashboard_offline.py`
- `tests/test_corrected_pipeline_regression.py`

## Pass A. Repository Structure

The corrected pipeline exists as separate modules:

| Pipeline stage | Main implementation |
|---|---|
| Sensor/Input Data | `examples/sample_daily_context.json`, legacy context/snapshot adapters |
| Current State Builder | `libsbapi/current_state_builder.py` |
| Environmental Predictor | `libsbapi/environmental_prediction.py` |
| Scenario Simulator | `libsbapi/scenario_comparison.py`, legacy `simulation_runner.py` |
| Threshold / Evidence Rule Engine | `libsbapi/evidence_rules.py`, `config/evidence_rules.json` |
| Work-Need Scorer | `libsbapi/work_need_scorer.py` |
| Recommendation Generator | `libsbapi/recommendation_generator.py` |
| Dashboard / Example Output | `dashboard/greenhouse_dashboard.py`, `libsbapi/offline_demo.py`, `examples/berrynext_today_recommendation.py` |

Measurable issue:

- There are pre-existing uncommitted production and test changes in the working tree. This audit did not change production code.

## Pass B. Data Flow Consistency

Observed offline path:

```text
examples/sample_daily_context.json
  -> CurrentStateBuilder.from_daily_context_file()
  -> NoChangeBaselinePredictor via predict_environment_delta()
  -> compare_action_candidates()
  -> WorkNeedScorer.score()
  -> auxiliary_alert_scores()
  -> RecommendationGenerator.generate()
  -> dashboard/example display helpers
```

Important finding:

- The main dashboard recommendation tab uses `build_demo()` and therefore the sample JSON. Sidebar sliders feed the secondary legacy/proxy simulator only. If a presenter changes sidebar values, the main recommendation cards do not change.

### Variable Trace Table

| Variable | Raw source | Normalized writer | Prediction input/output | Scenario input | Scorer input | Dashboard/example display | Risk |
|---|---|---|---|---|---|---|---|
| `air_temp` | `snapshot.inside_temperature_c` | `CurrentStateBuilder.from_daily_context()` | predicted by `NoChangeBaselinePredictor`; delta 0 | `GreenhouseEnvironment.inside_temperature_c` with fallback 22.0 if missing | used by shading/heating | current state, prediction table | fallback can hide missing input in scenario |
| `humidity` | `snapshot.inside_humidity_pct` | same | predicted; delta 0 | `GreenhouseEnvironment.humidity_pct` with fallback 70.0 | ventilation | current state, prediction table | fallback can weaken traceability if missing |
| `vpd` | `snapshot.vpd` or calculated from temp/RH | same; adds fallback warning | predicted; delta 0 | `GreenhouseEnvironment.vpd_kpa` with fallback 0.7 | irrigation, ventilation, shading | current state, prediction table | calculated VPD is good, but fallback defaults need clearer display |
| `solar_radiation` | `snapshot.solar_radiation_w_m2` | same | predicted; delta 0 | `GreenhouseEnvironment.solar_radiation_w_m2` with fallback 0.0 | irrigation, shading | current state, prediction table | no cumulative radiation in sample |
| `substrate_moisture` | `snapshot.substrate_moisture_pct` or copied from root-zone | builder syncs with root-zone when only one exists | not directly predicted unless target exists | scenario uses `root_zone_moisture` as `substrate_moisture_pct` | irrigation uses root/substrate | current state | naming is now displayed separately but source equivalence should be traceable |
| `root_zone_moisture` | `snapshot.root_zone_moisture_pct` | same | predicted; delta 0 | scenario substrate moisture | irrigation | current state, prediction table | sample value 31% drives high irrigation |
| `feed_ec` | `snapshot.feed_ec` | same | not in current target list | scenario `feed_ec` | EC scorer fallback option | current state | missing in sample; scorer still confident 0.56 |
| `drain_ec` | `snapshot.drainage_ec` or `snapshot.ec` | same | predicted; delta 0 | scenario `drain_ec` with fallback 1.5 if missing | EC scorer | current state, prediction table | sample `ec` is interpreted as drain EC |
| `root_ec` | `snapshot.root_ec` | same | not predicted | scenario fallback after drain EC | EC scorer fallback option | current state | missing in sample; confidence does not drop enough |
| `outside_temp` | `snapshot.outside_temp` or weather | builder | not predicted | not passed to scenario comparison | heating | current state | missing in sample; heating confidence still 0.56 after small penalty |
| `growth_stage` | top-level `growth_stage` | builder | not predicted | not passed to scenario comparison | auxiliary harvest | current state | Level 2 harvest alert can become high in sample |

Sample current state from `examples/sample_daily_context.json`:

- `air_temp=27.5`, `humidity=91.0`, `vpd=0.33`
- `solar_radiation=540.0`, `root_zone_moisture=31.0`, `drain_ec=1.3`
- missing: `feed_ec`, `root_ec`, `feed_ph`, `drainage_ratio`, `outside_temp`, `outside_humidity`, `time_of_day`, `timestamp`

## Pass C. Scoring and Ranking

The scorer implements five Level 1 actions only:

- `irrigation`
- `nutrient_ec_check`
- `ventilation_dehumidification`
- `shading_high_temperature`
- `heating_low_temperature`

Sample output:

| Action | Score | Status | Confidence |
|---|---:|---|---:|
| 환기 | 82 | recommend | 0.56 |
| 관수 | 76 | recommend | 0.56 |
| EC·양액 조절 | 0 | monitor | 0.56 |
| 차광 | 0 | monitor | 0.56 |
| 보온 또는 난방 검토 | 0 | monitor | 0.56 |

Sanity coverage:

| Case | Implemented | Tested | Notes |
|---|---|---|---|
| High humidity + low VPD + adequate moisture -> ventilation high, irrigation not high | Partially | Missing exact test | Ventilation high is tested. Adequate-moisture anti-irrigation case is not explicitly tested. |
| Low moisture + high VPD -> irrigation high | Yes | Yes | `test_predicted_low_substrate_moisture_makes_irrigation_high` |
| High root/drain EC -> EC·양액 조절 high | Yes | Yes | `test_predicted_high_ec_makes_nutrient_score_high` |
| High temperature + high radiation -> shading high | Yes | Yes | `test_predicted_high_temperature_and_radiation_makes_shading_high` |
| Low nighttime temperature -> heat preservation high | Yes | Yes | `test_predicted_low_night_temperature_makes_heating_high` |
| Normal condition -> no urgent recommendations | Yes | Yes | `test_normal_conditions_have_no_urgent_scores` |
| Missing key sensors -> lower confidence or human review | Partially | Partially | Missing sensor penalty exists, but confidence remains generic and human review is always true. |

Measurable issues:

- `WorkNeedScorer.score()` accepts `scenario_refs` but deletes it. Scenario results influence final explanation in `RecommendationGenerator`, not the numeric work-need score.
- Confidence is formula-based but still too generic. With evidence rules and no usable predictions, most sample actions receive `0.56`.
- Missing data penalties are small. Example: heating with missing outside temperature still has confidence around `0.56`.

## Pass D. Prediction Validity

Current dashboard/offline demo uses `NoChangeBaselinePredictor`.

| Target | Current value source | Predicted delta source | Predicted value calculation | model_used | fallback_used | confidence |
|---|---|---|---|---|---|---:|
| `air_temp` | current state | constant `0.0` | current + 0 | `no_change_baseline` | true | 0.20 |
| `humidity` | current state | constant `0.0` | current + 0 | `no_change_baseline` | true | 0.20 |
| `vpd` | current/calculated state | constant `0.0` | current + 0 | `no_change_baseline` | true | 0.20 |
| `solar_radiation` | current state | constant `0.0` | current + 0 | `no_change_baseline` | true | 0.20 |
| `root_zone_moisture` | current state | constant `0.0` | current + 0 | `no_change_baseline` | true | 0.20 |
| `drain_ec` | current state | constant `0.0` | current + 0 | `no_change_baseline` | true | 0.20 |

Status:

- v0 no-change baseline: implemented and used in offline demo.
- v1 rolling delta baseline: implemented and tested.
- v2 linear model: not implemented.
- v3 GAM: placeholder only. `GAMReadyPredictor` raises `NotImplementedError`.
- Real GAM training/inference: missing.

## Pass E. Scenario Simulator

`libsbapi/scenario_comparison.py` compares 10 candidate actions:

- `irrigation`, `no_irrigation`
- `lower_ec_nutrient_adjustment`, `raise_ec_check_supplied_ec`
- `ventilation`, `no_ventilation`
- `shading`, `no_shading`
- `heat_preservation_heating_review`, `no_heat_preservation`

Output fields include:

- moisture, EC, salinity, humidity, VPD, temperature deltas
- disease-environment risk proxy
- energy cost proxy
- confidence
- expected benefits, risks, warnings
- evidence rule IDs/tags
- `model_status="heuristic_prototype"`
- `is_training_label=False`

Measurable issues:

- Scenario output is heuristic and correctly marked as not training labels.
- Scenario output is visible in dashboard/examples and included in recommendation explanations.
- Scenario output is not currently used by `WorkNeedScorer` to calculate numeric scores.
- Scenario input uses hardcoded placeholder values for some fields such as `disease_risk=0.35`, `leaf_density=0.6`, and fallback `substrate_moisture_pct=50.0` when current moisture is missing.

## Pass F. Level 1 / Level 2 Separation

Level 1 main ranking is separated:

- 관수
- EC·양액 조절
- 환기
- 차광
- 보온 또는 난방 검토

Level 2 auxiliary alerts are separate:

- 병해 위험 예찰 알림
- 수확 가능성 알림
- 적엽 검토 알림

Measurable status:

- Dashboard helper tests verify Level 1 display list and Level 2 separation.
- Recommendation generator returns separate `level1_recommendations` and `auxiliary_alerts`.
- Evidence rules mark disease/harvest/leaf removal as `level2_auxiliary_alert`.

Risk:

- In machine-readable output, sample harvest and disease auxiliary alerts can still have status `recommend`. The dashboard display softens harvest `recommend` to `검토 필요`, but JSON/text consumers may still see `recommend` for Level 2.

## Pass G. Safety and Overclaim Check

Risky phrase search results:

| Phrase/location | Status | Recommended correction |
|---|---|---|
| `GAMReadyPredictor` and GAM docs | Safe | Correctly says planned/placeholder, not implemented. |
| `fake supervised farmwork label` in scenario notice/tests | Safe | It is used to prohibit fake labels. |
| `actual disease prediction` in rules/tests/docs | Safe | Used as negative claim. |
| `README.md` competition API section contains older AI control wording | Ambiguous | Keep if preserving external API examples, but visually separate from BerryNext decision-support docs. |
| Korean broken strings such as `경찰`, `레슬링`, `통풍구`, `관수센터` | Safe | Only remain in test banlist. |

No evidence was found that the current BerryNext pipeline claims real GAM, autonomous greenhouse control, supervised farmer-behavior learning, or validated disease/harvest/leaf-removal prediction.

## Commands Run

| Command | Result |
|---|---|
| `git status --short` | PASS, showed pre-existing uncommitted production/test changes plus audit artifacts |
| `python -m pytest` | FAIL: `/bin/bash: line 1: python: command not found` |
| `python3 -m pytest` | PASS: 137 passed |
| `python -m compileall libsbapi dashboard examples tests` | FAIL: `/bin/bash: line 1: python: command not found` |
| `python3 -m compileall libsbapi dashboard examples tests` | PASS |
| `python -m examples.berrynext_today_recommendation` | FAIL: `/bin/bash: line 1: python: command not found` |
| `python3 -m examples.berrynext_today_recommendation` | PASS |
| `python -m examples.greenhouse_scenario_compare` | FAIL: `/bin/bash: line 1: python: command not found` |
| `python3 -m examples.greenhouse_scenario_compare` | PASS |

Follow-up environment fix:

- The `python` failures were caused by a missing shell command alias, not by repository test failures.
- Fixed by creating `~/.local/bin/python -> /usr/bin/python3`.
- Re-ran the previously failing commands with `python`; all passed after the fix:
  - `python -m pytest`: PASS, 137 passed
  - `python -m compileall libsbapi dashboard examples tests`: PASS
  - `python -m examples.berrynext_today_recommendation`: PASS
  - `python -m examples.greenhouse_scenario_compare`: PASS

## Recommended Patch Plan

P0 reliability fixes:

1. Add an explicit test for high humidity + low VPD + adequate moisture:
   - ventilation high
   - irrigation not high
   - irrigation status `hold`, `monitor`, or at most `caution`
2. Make confidence action-specific and sensor-coverage based.
   - Example: EC score confidence should drop when `feed_ec` and `root_ec` are missing.
3. Decide whether the dashboard sidebar is a legacy/proxy-only control or should drive the main pipeline.
   - If proxy-only, label it clearly.
   - If interactive demo, wire sidebar values into `CurrentStateBuilder` or a dashboard state payload.
4. Remove hidden fallback defaults from scenario inputs or expose them as quality warnings.
5. Make Level 2 machine-readable statuses less action-like, such as `monitor`, `caution`, or a separate alert status field.

P1 model and agronomy fixes:

1. Add rolling-history example input and use v1 rolling delta where history exists.
2. Keep v0 no-change as fallback and never call it GAM.
3. Integrate scenario comparison into scoring only when explicitly designed and tested.
4. Validate evidence thresholds with citations and local greenhouse calibration.
5. Add data-quality/unit validation for moisture, EC, VPD, humidity, and timestamps.

P2 future extensions:

1. Add real GAM training/inference only behind the existing prediction contract.
2. Add image-based Level 2 alert support only with explicit image/proxy tests.
3. Add dashboard trace panel showing raw input, normalized state, prediction input, scenario input, scorer input, and displayed output.

## Final Judgment

BerryNext is currently credible for a university presentation as an explainable offline prototype if it is described honestly:

- rule-based decision support
- conservative baseline prediction
- heuristic scenario comparison
- human review required
- no autonomous control
- no real GAM yet
- no validated disease/harvest/leaf-removal prediction

It is not yet functionally trustworthy for real greenhouse operational decisions because confidence, state consistency, calibration, and real short-term prediction are still prototype-level.
