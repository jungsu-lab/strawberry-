# BerryNext Final Functional Verification

Date: 2026-06-25

## 1. Branch and commit status

| Item | Result |
|---|---|
| Branch | `feature/greenhouse-dashboard` |
| Last commit | `4962b7b Implement BerryNext decision-support pipeline` |
| Working tree | Uncommitted changes remain in dashboard, examples, `libsbapi`, tests, `AGENT_MEMORY.md`, scripts, and reports. |

The verification was run against the current local working tree, not only the last commit.

## 2. What the system currently does

BerryNext currently runs offline as an explainable strawberry greenhouse decision-support prototype.

It can:

- load sample daily greenhouse context
- normalize sensor values into a current greenhouse state
- run 1 to 3 hour no-change baseline environmental predictions
- compare Level 1 greenhouse management action candidates with heuristic scenario outputs
- load structured literature/manual/prototype evidence rules
- calculate Level 1 work-need scores for irrigation, EC/nutrient adjustment, ventilation, shading, and heat preservation
- generate ranked human-readable recommendations
- keep disease, harvest, and leaf-removal as separate Level 2 auxiliary proxy alerts
- show safety wording: `decision_support`, human review required, and not autonomous control

## 3. What the system does not do

BerryNext does not run real autonomous greenhouse control.

Real GAM training or inference is not active. Current demo predictions are baseline predictions, mainly `no_change_baseline`, with `predicted_delta = 0` and `predicted_value = current_value`.

The system does not learn farmer behavior from farmwork-history labels and does not use simulation outputs as fake supervised farmwork labels.

Disease, harvest, and leaf-removal outputs are Level 2 proxy alerts, not validated disease diagnosis, validated harvest prediction, or direct leaf-removal prescription.

## 4. Architecture verification

| Stage | Implemented | Files | Tests | Known limitations |
|---|---|---|---|---|
| Sensor/Input Data | yes | `examples/sample_daily_context.json`, dashboard sidebar inputs | `tests/test_state_flow_consistency.py`, example smoke tests | More real hourly sensor history and unit validation are needed. |
| Current State Builder | yes | `libsbapi/current_state_builder.py` | `tests/test_state_flow_consistency.py`, current-state tests | Some fields use explicit proxy warnings, for example substrate moisture from root-zone moisture. |
| Environmental Predictor | partial | `libsbapi/environmental_prediction.py`, `libsbapi/decision_contract.py` | `tests/test_prediction_baseline_contract.py`, environmental prediction tests | v0/v1 baselines exist. Real GAM is not implemented. |
| Scenario Simulator | yes, heuristic | `libsbapi/scenario_comparison.py`, `examples/greenhouse_scenario_compare.py` | `tests/test_short_horizon_scenario_comparison.py`, scenario example tests | Outputs are heuristic prototype comparisons and not physical ground truth. |
| Threshold / Evidence Rule Engine | yes | `libsbapi/evidence_rules.py`, `config/evidence_rules.json` | `tests/test_evidence_rules.py`, pipeline regression tests | Thresholds still need literature citation cleanup and local calibration. |
| Work-Need Scorer | yes | `libsbapi/work_need_scorer.py` | `tests/test_recommendation_sanity.py`, `tests/test_confidence_logic.py`, scorer tests | Confidence is sensor-coverage based but still prototype-level. |
| Recommendation Generator | yes | `libsbapi/recommendation_generator.py`, `libsbapi/offline_demo.py` | `tests/test_recommendation_generator.py`, example tests | Level 2 CLI alert status can still print `추천`; it is separated but should be softened in future output. |
| Dashboard / Example Output | yes | `dashboard/greenhouse_dashboard.py`, `examples/berrynext_today_recommendation.py` | `tests/test_greenhouse_dashboard_offline.py`, display-label tests | Dashboard should remain demo-only until validated with real greenhouse data. |

Architecture:

```text
Sensor/Input Data
-> Current State Builder
-> Environmental Predictor
-> Scenario Simulator
-> Threshold / Evidence Rule Engine
-> Work-Need Scorer
-> Recommendation Generator
-> Dashboard / Example Output
```

## 5. Measurable test results

| Check | Command | Result | Notes |
|---|---|---|---|
| Repository status | `git status --short` | PASS | Shows uncommitted local changes. |
| Branch | `git branch --show-current` | PASS | `feature/greenhouse-dashboard` |
| Compile check | `python -m compileall libsbapi dashboard examples tests` | PASS | Exit code 0. |
| Unit tests | `python -m pytest -q` | PASS | `167 passed in 1.63s` |
| Offline recommendation demo | `python -m examples.berrynext_today_recommendation` | PASS | Prints current state, baseline predictions, scenario comparison, Level 1 recommendations, and Level 2 alerts. |
| Scenario comparison demo | `python -m examples.greenhouse_scenario_compare` | PASS | Prints Level 1 candidate comparison and says outputs are not fake supervised labels. |
| State flow audit | `python scripts/audit_state_flow.py` | PASS | Prints raw/current/predicted/scenario/scorer/dashboard trace table. |
| Bad string search | `rg -n "...banlist..." ...` | PASS with classified findings | Broken Korean strings remain only in banlists/old report. Risk phrases remain in negative safety contexts. |
| Streamlit availability | `command -v streamlit`; `curl -I http://localhost:8501` | PASS | Streamlit exists at `/home/jungsu/.local/bin/streamlit`; existing local server returned HTTP 200. |

Non-release helper note: an ad hoc score extraction snippet initially failed because it imported the wrong prediction class and then passed a prediction object shape not expected by the scorer gate. This did not affect the required release checks; current-state score extraction was rerun successfully.

## 6. Recommendation sanity matrix

| Scenario | Expected | Actual | Pass/Fail |
|---|---|---|---|
| High humidity + low VPD + adequate moisture | Ventilation high; irrigation not aggressive | Ventilation `82/recommend`; irrigation `34/hold` | Pass |
| Low moisture + high VPD | Irrigation high | Irrigation `100/recommend` | Pass |
| High EC | EC/nutrient adjustment high | EC/nutrient `74/recommend` | Pass |
| High temperature + high radiation | Shading high | Shading `92/recommend` | Pass |
| Low nighttime temperature | Heat preservation high and energy warning expected | Heat preservation `90/recommend`; scenario output includes energy cost | Pass |
| Normal condition | No urgent recommendations | No score reaches recommendation threshold; irrigation remains `34/hold` | Pass with caveat |
| Missing sensors | Lower confidence or human review | Missing-sensor case lowers confidence and keeps human review required | Pass |
| No-change baseline prediction | Delta 0, predicted equals current, not real GAM | Demo prints `no_change_baseline`, `+0.00`, baseline/fallback wording | Pass |

## 7. Remaining risks

- Real GAM training and inference still need implementation and validation.
- Literature/manual thresholds need citation cleanup and greenhouse-specific local calibration.
- Scenario simulation is heuristic/prototype and should not be treated as physical truth.
- Dashboard must not be used for real autonomous control.
- Sensor mapping and unit validation need more real data, especially moisture, root EC, drain EC, outside weather, and time-of-day fields.
- Level 2 auxiliary alerts are separated, but CLI output can still show `추천` for disease/harvest proxy alerts. For presentation, the dashboard wording is safer; future CLI output should soften these statuses to `검토 필요` or `모니터링`.
- Normal-condition irrigation score can remain `hold` around 34 due prototype caution logic. This is not urgent, but threshold calibration should refine it.

## 8. Presentation-safe wording

현재 BerryNext는 센서 기반 현재 상태와 기준선 예측, 문헌/매뉴얼 기반 룰, 휴리스틱 시나리오 비교를 결합해 관수, EC·양액 조절, 환기, 차광, 보온의 필요도를 계산하는 의사결정 보조 프로토타입입니다.

BerryNext는 자율제어를 실행하지 않으며, 농가 작업 이력 라벨을 학습해 작업을 대신 결정하거나 병해·수확·적엽을 확정적으로 예측하는 시스템이 아닙니다.

향후에는 실제 단기 환경 변화 예측을 위한 GAM 또는 다른 모델 학습, 문헌 임계값 검증과 농가별 보정, 더 정밀한 센서 품질 검증과 이미지 기반 보조 알림 검증이 필요합니다.

## 9. Final verdict

Ready with caveats.

BerryNext is ready for a prototype demo because it runs offline, passes compile and unit tests, demonstrates the corrected decision-support pipeline, separates Level 1 recommendations from Level 2 auxiliary alerts, and avoids claiming active GAM or autonomous control in the main demo path.

It is not ready for operational greenhouse decision automation. Remaining caveats are baseline-only prediction, heuristic simulation, prototype threshold calibration, incomplete real-data validation, and Level 2 proxy status wording in the CLI output.
