# BerryNext Agent Memory

## 0. Project North Star

BerryNext is an explainable strawberry greenhouse decision-support prototype.

It recommends today's greenhouse management priorities by combining:

1. current sensor state
2. short-term environmental prediction
3. scenario comparison
4. literature/manual-based threshold rules
5. work-need scoring
6. human-readable recommendation output

BerryNext is NOT:

- an autonomous greenhouse controller
- a model that learns farmer behavior from farmwork-history labels
- a direct disease, harvest, or leaf-removal prediction model
- a fake-label supervised learning system
- a completed GAM model unless real GAM training/inference is implemented and tested

## 1. Core Level 1 Actions

The main ranked recommendation list must contain only:

| Internal ID | Korean Label |
|---|---|
| irrigation | 관수 |
| nutrient_ec_adjustment | EC·양액 조절 |
| ventilation | 환기 |
| shading | 차광 |
| heat_preservation | 보온 또는 난방 검토 |

## 2. Level 2 Auxiliary Alerts

These are not core recommendations. They are separate proxy alerts.

| Internal ID | Korean Label |
|---|---|
| disease_risk_scouting_alert | 병해 위험 예찰 알림 |
| harvest_possibility_alert | 수확 가능성 알림 |
| leaf_removal_review_alert | 적엽 검토 알림 |

Required wording:

"이 알림은 방제, 수확, 적엽을 직접 추천하는 핵심 모델이 아니라, 보조 알림 프록시입니다."

## 3. Functional Architecture

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

## 4. Non-Negotiable Safety Text

Every final recommendation output or dashboard must clearly say:

* decision_support
* 사람 검토 필요
* 자율제어 아님

Required Korean safety sentence:

"권장사항은 자율제어를 실행하지 않으며, 실제 작업 전 온실 상태와 작업 가능 여부를 사람이 확인해야 합니다."

## 5. Current Known Risks

Update this list after every goal.

### Risk A. Prediction overclaim

Current predictor may be a no-change or baseline predictor.
Do not call it real GAM unless GAM is actually implemented and tested.

### Risk B. State mismatch

Check whether sidebar/input values match normalized current state and scorer state.
Special watch variables:

* moisture
* substrate_moisture
* root_zone_moisture
* drain_ec
* root_ec
* humidity
* vpd
* air_temp

### Risk C. Irrigation logic conflict

High humidity + low VPD + adequate moisture should not produce an aggressive irrigation recommendation.

### Risk D. Generic confidence

Confidence should be action-specific or sensor-coverage-based.
Avoid one fixed confidence value for every action unless explicitly documented.

### Risk E. Level 2 overclaim

Disease, harvest, and leaf-removal outputs must remain auxiliary proxy alerts.

## 6. Measurable Quality Gates

### Gate 1. State consistency

For the same input scenario, the following states must be traceable and not silently inconsistent:

* raw input state
* normalized current state
* prediction input state
* scenario input state
* scorer input state
* dashboard displayed state

### Gate 2. Prediction contract

No-change baseline must satisfy:

* predicted_delta = 0
* predicted_value = current_value
* model_used = "no_change_baseline"
* fallback_used = true or explicitly documented
* dashboard must not describe this as real GAM

### Gate 3. Recommendation sanity cases

The test suite must include at least:

1. high humidity + low VPD + adequate moisture
   -> ventilation high, irrigation not high

2. low moisture + high VPD
   -> irrigation high

3. high EC
   -> EC·양액 조절 high

4. high temperature + high radiation
   -> shading high

5. low nighttime temperature
   -> heat preservation high

6. normal state
   -> no urgent recommendations

7. missing key sensors
   -> lower confidence or human review required

### Gate 4. Level separation

Main ranked recommendations must include only Level 1 actions.
Level 2 alerts must be separate.

### Gate 5. Safety copy

No output may claim autonomous control.

## 7. Bad Strings Banlist

User-facing dashboard/example output must not contain these broken strings:

* 경찰
* 결정팀
* 레슬링
* 통풍구
* 운동
* 관수센터
* 강우 재미
* 정말
* 알림을 위한 알림
* 상태가 최종임
* 일별 입장
* 사용자 로그인

Any remaining occurrence must be justified as a test fixture or old report.

## 8. Fast Feedback Loop Protocol

For every goal:

1. Read this file first.
2. Write a short plan under "Current Goal Log".
3. Change at most 1 to 3 related files per micro-cycle.
4. After each micro-cycle, run the narrowest relevant test.
5. Record PASS/FAIL in this file.
6. If the same test fails twice, stop broad changes and report the blocker.
7. Run full tests only after narrow tests pass.
8. Never hide failed commands.

## 9. Current Goal Log

Append entries like this:

### YYYY-MM-DD HH:MM - Goal name

Objective:

Files inspected:

Files changed:

Narrow tests run:

Result:

Failed command, if any:

Decision made:

Next step:

### 2026-06-25 18:45 - Dashboard Korean copy and presentation readiness

Objective:

Make the Streamlit dashboard and offline examples presentation-ready in Korean while preserving the corrected BerryNext decision-support direction.

Files inspected:

`dashboard/`, `examples/`, `libsbapi/recommendation_generator.py`, `libsbapi/offline_demo.py`, `libsbapi/scenario_comparison.py`, `README.md`, `docs/`, `config/evidence_rules.json`, `tests/`.

Files changed:

`dashboard/greenhouse_dashboard.py`, `examples/greenhouse_scenario_compare.py`, `libsbapi/display_labels.py`, `libsbapi/offline_demo.py`, `libsbapi/recommendation_generator.py`, `libsbapi/scenario_comparison.py`, and related tests.

Narrow tests run:

`python3 -m unittest tests.test_display_labels tests.test_greenhouse_dashboard_offline tests.test_recommendation_generator tests.test_berrynext_today_recommendation_example tests.test_greenhouse_scenario_compare_example`

Result:

PASS.

Failed command, if any:

`python -m pytest` failed because this environment has no `python` alias. Use `python3 -m pytest`.

Decision made:

Centralized user-facing Korean labels in `libsbapi/display_labels.py`. Dashboard and examples should use natural Korean display labels while preserving stable English internal IDs.

Next step:

Keep checking state consistency between dashboard sidebar inputs, normalized current state, scenario input, scorer input, and displayed state.

### 2026-06-25 19:00 - Functional trustworthiness audit

Objective:

Objectively audit whether BerryNext is functionally trustworthy as a decision-support prototype without modifying production code.

Files inspected:

`README.md`, `BERRYNEXT_AI_PLAN.md`, `DESIGN.md`, `docs/`, `config/evidence_rules.json`, `examples/sample_daily_context.json`, `examples/berrynext_today_recommendation.py`, `examples/greenhouse_scenario_compare.py`, `dashboard/greenhouse_dashboard.py`, `libsbapi/current_state_builder.py`, `libsbapi/decision_contract.py`, `libsbapi/environmental_prediction.py`, `libsbapi/evidence_rules.py`, `libsbapi/work_need_scorer.py`, `libsbapi/recommendation_generator.py`, `libsbapi/scenario_comparison.py`, `libsbapi/offline_demo.py`, `libsbapi/auxiliary_alert_scoring.py`, `libsbapi/display_labels.py`, `libsbapi/action_recommenders/`, and relevant tests.

Files changed:

Allowed audit artifacts only: `AGENT_MEMORY.md` and `docs/reports/functional_audit.md`.

Narrow tests run:

`python -m pytest` failed because this environment has no `python` alias.
`python3 -m pytest` passed 137 tests.
`python -m compileall libsbapi dashboard examples tests` failed because this environment has no `python` alias.
`python3 -m compileall libsbapi dashboard examples tests` passed.
`python -m examples.berrynext_today_recommendation` failed because this environment has no `python` alias.
`python3 -m examples.berrynext_today_recommendation` passed.
`python -m examples.greenhouse_scenario_compare` failed because this environment has no `python` alias.
`python3 -m examples.greenhouse_scenario_compare` passed.

Result:

Completed audit. BerryNext is functionally trustworthy as a transparent offline decision-support prototype, but not yet trustworthy for real operational greenhouse decisions.

Failed command, if any:

`python -m pytest`, `python -m compileall libsbapi dashboard examples tests`, `python -m examples.berrynext_today_recommendation`, and `python -m examples.greenhouse_scenario_compare` failed with `/bin/bash: line 1: python: command not found`.

Decision made:

Do not edit production code during this goal. Record findings and recommended patch plan only.

Audit findings:

* Main dashboard recommendation tab uses `examples/sample_daily_context.json`; sidebar sliders drive the secondary proxy simulator, not the main recommendation pipeline.
* Current demo prediction is v0 no-change baseline with `predicted_delta=0`, `fallback_used=true`, and confidence `0.20`.
* Rolling baseline exists and is tested; real GAM is not implemented.
* Scenario comparison is heuristic, not training-label generation, and is visible in examples/dashboard.
* Scenario outputs feed recommendation explanation but are not used by `WorkNeedScorer.score()` for numeric scores.
* Work-need confidence is still generic: sample Level 1 actions receive `0.56` even when some action-specific sensors are missing.
* Level 1 and Level 2 outputs are separated, but Level 2 machine-readable alerts can still carry `recommend` status.
* No broken Korean dashboard strings remain outside test banlists.
* Follow-up environment fix: created `~/.local/bin/python -> /usr/bin/python3`, then `python -m pytest`, `python -m compileall libsbapi dashboard examples tests`, `python -m examples.berrynext_today_recommendation`, and `python -m examples.greenhouse_scenario_compare` all passed.

Next step:

Implement recommended P0 reliability fixes only after user approval: adequate-moisture anti-irrigation sanity test, action-specific confidence, clearer sidebar/main-pipeline state flow, explicit scenario fallback warnings, and safer Level 2 alert status semantics.

## 10. Last Verified Commands

Append the latest verified commands here.

```text
python -m pytest
python -m compileall libsbapi dashboard examples tests
python -m examples.berrynext_today_recommendation
python -m examples.greenhouse_scenario_compare
```

### 2026-06-25 18:45

```text
python3 -m pytest
python3 -m py_compile $(git ls-files '*.py') $(git ls-files --others --exclude-standard '*.py')
python3 -m examples.berrynext_today_recommendation
python3 -m examples.greenhouse_scenario_compare
git diff --check
streamlit run dashboard/greenhouse_dashboard.py
curl -I http://localhost:8501
```

### 2026-06-25 19:00

```text
git status --short
python -m pytest
python3 -m pytest
python -m compileall libsbapi dashboard examples tests
python3 -m compileall libsbapi dashboard examples tests
python -m examples.berrynext_today_recommendation
python3 -m examples.berrynext_today_recommendation
python -m examples.greenhouse_scenario_compare
python3 -m examples.greenhouse_scenario_compare
```

### 2026-06-25 19:20

```text
ln -sfn /usr/bin/python3 /home/jungsu/.local/bin/python
python --version
python -m pytest
python -m compileall libsbapi dashboard examples tests
python -m examples.berrynext_today_recommendation
python -m examples.greenhouse_scenario_compare
```

## 11. Open TODOs

* Real GAM training and inference
* Literature threshold citation cleanup
* Local calibration by greenhouse/farm
* Better hourly history support
* More robust sensor quality handling
* Image-based Level 2 alerts

### 2026-06-25 19:30 - Goal 1 - State Flow Consistency

Objective:

Fix or prove functional consistency of BerryNext state flow for moisture, EC, humidity, VPD, air temperature, and solar radiation.

Files inspected:

`AGENT_MEMORY.md`, `docs/reports/functional_audit.md`, `libsbapi/current_state_builder.py`, `libsbapi/offline_demo.py`, `libsbapi/work_need_scorer.py`, `dashboard/greenhouse_dashboard.py`, `libsbapi/environmental_prediction.py`, `libsbapi/scenario_comparison.py`, existing state/current/scorer/dashboard tests.

Files changed:

`libsbapi/current_state_builder.py`, `libsbapi/offline_demo.py`, `libsbapi/work_need_scorer.py`, `scripts/audit_state_flow.py`, `tests/test_state_flow_consistency.py`, `AGENT_MEMORY.md`.

Narrow tests run:

Cycle 1: `python -m compileall libsbapi dashboard examples tests` PASS.
Cycle 2: `python scripts/audit_state_flow.py` failed once due missing repo root on `sys.path`, then PASS after adding repo root.
Cycle 3: `python -m pytest tests/test_state_flow_consistency.py -q` first RED failed 4 expected tests, then PASS with 9 tests.
Related: `python -m pytest tests/test_current_state_builder.py tests/test_work_need_scorer.py tests/test_greenhouse_dashboard_offline.py tests/test_berrynext_today_recommendation_example.py -q` PASS, 27 tests.
Cycle 4: `python -m pytest -q` PASS, 146 tests.
Examples: `python -m examples.berrynext_today_recommendation` PASS; `python -m examples.greenhouse_scenario_compare` PASS.

Result:

Completed.

Failed command, if any:

Expected RED: `python -m pytest tests/test_state_flow_consistency.py -q` failed before implementation because audit script was missing, substrate/root-zone moisture proxy warning was missing, scenario adapter changed `0.0` to defaults, and partial EC sensor coverage did not reduce confidence.
Cycle 2 first run: `python scripts/audit_state_flow.py` failed with `ModuleNotFoundError: No module named 'libsbapi'`; fixed by adding repo root to `sys.path`.

Decision made:

Exact path traced and tested: raw input -> normalized current state -> prediction input/output -> scenario input -> scorer input -> dashboard displayed state.

State flow fixes:

* Current state builder now records explicit quality warnings when `substrate_moisture` is filled from `root_zone_moisture` or vice versa.
* Scenario adapter now preserves valid zero values by checking `is not None` instead of using truthiness fallback.
* EC confidence now decreases when only partial EC fields are available.
* `scripts/audit_state_flow.py` prints an offline state flow table for watched variables.

Next step:

Remaining risk: main dashboard still uses sample JSON for the primary recommendation pipeline while sidebar controls feed the secondary simulator; this is now traceable but not yet made interactive.

### 2026-06-25 20:05 - Goal 1 follow-up - Remove remaining state-flow risks

Objective:

Resolve the remaining risks from Goal 1: connect main dashboard recommendations to sidebar input, expose scenario prototype placeholders, and make confidence more sensor-coverage based.

Files inspected:

`dashboard/greenhouse_dashboard.py`, `libsbapi/offline_demo.py`, `libsbapi/work_need_scorer.py`, `scripts/audit_state_flow.py`, `tests/test_state_flow_consistency.py`, `tests/test_greenhouse_dashboard_offline.py`.

Files changed:

`dashboard/greenhouse_dashboard.py`, `libsbapi/offline_demo.py`, `libsbapi/work_need_scorer.py`, `scripts/audit_state_flow.py`, `tests/test_state_flow_consistency.py`, `tests/test_greenhouse_dashboard_offline.py`, `AGENT_MEMORY.md`.

Narrow tests run:

RED: `python -m pytest tests/test_state_flow_consistency.py tests/test_greenhouse_dashboard_offline.py -q` failed because the new current-state injection, scenario warning, and dashboard helper APIs did not exist yet.
GREEN: same command passed 24 tests.
Related: `python -m pytest tests/test_work_need_scorer.py tests/test_corrected_pipeline_regression.py tests/test_recommendation_generator.py tests/test_berrynext_today_recommendation_example.py tests/test_greenhouse_scenario_compare_example.py -q` passed 18 tests.
Full: `python -m pytest -q` passed 150 tests.
Smoke: `python -m examples.berrynext_today_recommendation`, `python -m examples.greenhouse_scenario_compare`, `python scripts/audit_state_flow.py`, and `python -m compileall libsbapi dashboard examples tests scripts` passed.
Dashboard: `streamlit run dashboard/greenhouse_dashboard.py --server.address 0.0.0.0 --server.port 8501` started, and `curl -I http://localhost:8501` returned 200 OK.

Result:

Completed.

Failed command, if any:

Expected RED failures only. No final failing command.

Decision made:

* Main dashboard recommendations now use sidebar current-state inputs via `build_demo_from_current_state`.
* Scenario input now uses context image/weather proxies when available and emits explicit `scenario_input_warnings` for remaining prototype placeholders.
* Work-need confidence now includes action-specific sensor coverage.

Next step:

Remaining project risks are now higher-level: real GAM training/inference, literature calibration, hourly history support, and validated image-based Level 2 alerts.

### 2026-06-25 20:30 - Goal 2 - Recommendation Sanity and Confidence

Objective:

Make BerryNext recommendation scores functionally sane and measurable across wet, dry, high EC, ventilation, shading, heating, normal, missing-sensor, baseline prediction, and confidence cases.

Files inspected:

`AGENT_MEMORY.md`, `docs/reports/functional_audit.md`, `scripts/audit_state_flow.py` output, `libsbapi/work_need_scorer.py`, `libsbapi/recommendation_generator.py`, `libsbapi/environmental_prediction.py`, `dashboard/greenhouse_dashboard.py`, existing scorer/recommendation tests.

Files changed:

`tests/test_recommendation_sanity.py`, `tests/test_prediction_baseline_contract.py`, `tests/test_confidence_logic.py`, `libsbapi/work_need_scorer.py`, `libsbapi/recommendation_generator.py`, `AGENT_MEMORY.md`.

Narrow tests run:

Cycle 1 RED: `python -m pytest tests/test_recommendation_sanity.py -q` failed 1 test because wet/high-humidity adequate-moisture irrigation monitor reason did not mention over-wet/disease-environment risk.
Cycle 2 GREEN: `python -m pytest tests/test_recommendation_sanity.py -q` passed 9 tests after adding irrigation wet-condition risk component and monitor-state component reasons.
Cycle 3: `python -m pytest tests/test_prediction_baseline_contract.py -q` passed 4 tests; no baseline code changes needed.
Cycle 5: `python -m pytest tests/test_confidence_logic.py -q` passed 4 tests.
Related: `python -m pytest tests/test_recommendation_sanity.py tests/test_prediction_baseline_contract.py tests/test_confidence_logic.py tests/test_work_need_scorer.py tests/test_recommendation_generator.py -q` passed 32 tests.
Cycle 6: `python -m pytest -q` passed 167 tests.
Compile: `python -m compileall libsbapi dashboard examples tests` passed.
Smoke: `python -m examples.berrynext_today_recommendation` and `python scripts/audit_state_flow.py` passed.

Result:

Completed.

Failed command, if any:

Expected RED only: `tests/test_recommendation_sanity.py::test_wet_low_vpd_adequate_moisture_prioritizes_ventilation_not_irrigation` failed before implementation because irrigation monitor reasons were generic.

Decision made:

Recommendation sanity is now measurable with deterministic tests for wet, dry, high EC, ventilation, shading, heating, normal, missing sensor, baseline, and confidence cases.

Scoring/reason fixes:

* Wet, low-VPD, adequate-moisture conditions keep irrigation non-aggressive while carrying a disease-environment/over-wet risk explanation.
* Monitor recommendations can now include relevant component reasons instead of only generic "no strong signal" text.
* Existing sensor-coverage confidence is tested directly across actions.

Next step:

Remaining project risks are outside this goal: real GAM integration, local threshold calibration, richer hourly history, and validated Level 2 image/proxy models.

### 2026-06-25 19:02 - Goal 3 - Final Functional Verification

Objective:

Verify whether BerryNext is ready for a prototype demo with measurable command results and a final report.

Files inspected:

`AGENT_MEMORY.md`, `docs/reports/functional_audit.md`, state-flow/recommendation/prediction/confidence/scenario/dashboard test files.

Files changed:

`AGENT_MEMORY.md`, `docs/reports/final_functional_verification.md`.

Narrow tests run:

Group 1: `git status --short` PASS; `git branch --show-current` PASS (`feature/greenhouse-dashboard`).
Group 2: `python -m compileall libsbapi dashboard examples tests` PASS.
Group 3: `python -m pytest -q` PASS, 167 tests.
Group 4: `python -m examples.berrynext_today_recommendation` PASS.
Group 5: `python -m examples.greenhouse_scenario_compare` PASS.
Group 6: `python scripts/audit_state_flow.py` PASS.
Group 7: bad-string/risky-claim `rg` search completed.
Group 8: Streamlit availability check PASS: `command -v streamlit` found `/home/jungsu/.local/bin/streamlit`; existing `http://localhost:8501` returned HTTP 200.

Result:

Completed.

Failed command, if any:

No required verification command failed.

Auxiliary helper failure: a one-off score extraction snippet failed first due `ImportError: cannot import name 'EnvironmentalPredictionResult'` and then due prediction object shape mismatch (`AttributeError: 'EnvironmentalPrediction' object has no attribute 'metrics'`). It was not a release check; current-state score extraction was rerun successfully.

Decision made:

Final verdict is `Ready with caveats`: ready for prototype demo, not ready for operational autonomous greenhouse use.

Next step:

Review `docs/reports/final_functional_verification.md` before PR/presentation. If committing, include the untracked report, memory, scripts, new label map, and tests.

Report:

`docs/reports/final_functional_verification.md`

### 2026-06-25 19:08 - Sidebar UI/UX and Korean label cleanup

Objective:

Reorganize the Streamlit sidebar around the final recommendation input structure and remove temporary or ambiguous Korean labels.

Files inspected:

`dashboard/greenhouse_dashboard.py`, `tests/test_greenhouse_dashboard_offline.py`, `libsbapi/display_labels.py`, `libsbapi/offline_demo.py`, `libsbapi/auxiliary_alert_scoring.py`.

Files changed:

`dashboard/greenhouse_dashboard.py`, `tests/test_greenhouse_dashboard_offline.py`, `AGENT_MEMORY.md`.

Narrow tests run:

RED: `python -m pytest tests/test_greenhouse_dashboard_offline.py -q` failed because the new sidebar sections and state fields were not implemented.
GREEN: `python -m pytest tests/test_greenhouse_dashboard_offline.py -q` passed 14 tests.
Related: `python -m pytest tests/test_greenhouse_dashboard_offline.py tests/test_display_labels.py tests/test_berrynext_today_recommendation_example.py tests/test_greenhouse_scenario_compare_example.py tests/test_recommendation_sanity.py tests/test_confidence_logic.py -q` passed 34 tests.
Full: `python -m pytest -q` passed 169 tests.
Compile: `python -m compileall libsbapi dashboard examples tests` passed.
Examples: `python -m examples.berrynext_today_recommendation` and `python -m examples.greenhouse_scenario_compare` passed.
Dashboard: existing `http://localhost:8501` returned HTTP 200.

Result:

Completed.

Failed command, if any:

Expected RED only for the new sidebar structure tests.

Decision made:

Main sidebar now follows:

1. 생육 단계 / 시간 정보
2. Level 1 핵심 온실 상태
3. 외부 환경 / 예측 보조
4. 선택 입력: Level 2 보조 알림

UI labels are Korean and presentation-oriented. Internal state still normalizes growth stage and time-of-day to logic-friendly values such as `harvest` and `night`.

Next step:

If committing, include the updated dashboard and tests. Remaining caveat: CLI Level 2 status wording can still be softened later.

### 2026-06-25 19:12 - Monitor recommendation risk cleanup and state-flow check

Objective:

Verify whether 0-point EC/shading/heating monitor outputs are correct, verify state-flow consistency, and verify high-humidity/low-VPD/adequate-moisture irrigation suppression.

Files inspected:

`scripts/audit_state_flow.py`, `libsbapi/recommendation_generator.py`, `libsbapi/offline_demo.py`, `tests/test_recommendation_generator.py`, dashboard output strings.

Files changed:

`libsbapi/recommendation_generator.py`, `tests/test_recommendation_generator.py`, `AGENT_MEMORY.md`.

Narrow tests run:

RED: `python -m pytest tests/test_recommendation_generator.py::RecommendationGeneratorTest::test_monitor_recommendations_do_not_show_action_scenario_risks -q` failed because monitor recommendations still included scenario effects/risks.
GREEN: same command passed after suppressing scenario effects/risks for `monitor` status.
Related: `python -m pytest tests/test_recommendation_sanity.py tests/test_recommendation_generator.py tests/test_greenhouse_dashboard_offline.py -q` passed 32 tests.
Full: `python -m pytest -q` passed 170 tests.
Compile: `python -m compileall libsbapi dashboard examples tests` passed.
State audit: `python scripts/audit_state_flow.py` passed.
Dashboard: restarted Streamlit on `http://localhost:8501`, HTTP 200.

Result:

Completed.

Failed command, if any:

Expected RED only.

Decision made:

0-point monitor scores are valid when no EC, shading, or heating signal exists, but monitor cards should not show action scenario risks because that makes them look like active recommendations.

Verification:

* Default dashboard-like state: EC, shading, heating are `0/monitor`.
* High humidity + low VPD + adequate moisture: ventilation `82/recommend`, irrigation `34/hold`.
* State-flow audit confirms watched values are traceable across current state, prediction, scenario, scorer, and dashboard display.

Next step:

Refresh browser at `http://localhost:8501` to clear any stale Streamlit view.

Observation:

State flow is traceable. `substrate_moisture` is explicitly marked as a proxy for `root_zone_moisture` in the sample context, and missing EC fields are exposed as quality warnings.

Bad-string classification:

* Broken Korean strings remain only in `AGENT_MEMORY.md` banlist, `tests/test_greenhouse_dashboard_offline.py` banlist, and `docs/reports/functional_audit.md` old audit summary.
* `autonomous control` remains in negative/safety contexts. One sample JSON warning uses the English phrase and should be translated later if that sample is shown directly to Korean users.

Observation:

Offline example clearly states `decision_support`, human review, no active GAM, baseline predictions, and Level 1 / Level 2 separation. Remaining caveat: Level 2 auxiliary alerts can still display status `추천` in the CLI text, even though they are separated from Level 1.
