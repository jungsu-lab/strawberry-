# Project Audit

Date: 2026-06-25

## Scope

This audit describes the current repository state before new implementation work. It separates code and behavior that are already implemented from planned or missing features for the strawberry smart-farm decision-support system.

Repository root: `/home/jungsu0327/strawberry-`

## Current Folder Structure

```text
.
├── BERRYNEXT_AI_PLAN.md
├── DAILY_CONTEXT_SCHEMA_KO.md
├── DATASET_MAPPING_KO.md
├── DESIGN.md
├── README.md
├── README_DATAMART_KO.md
├── STRAWBERRY_DATA_ROOM_KO.md
├── dashboard/
│   └── greenhouse_dashboard.py
├── docs/
│   └── project_audit.md
├── examples/
│   ├── berrynext_decision.py
│   ├── build_daily_context.py
│   ├── build_daily_context_from_excel.py
│   ├── control_priv.py
│   ├── daily_farmwork.py
│   ├── greenhouse_scenario_compare.py
│   ├── greenhouse_simulator.py
│   ├── nutsupply.py
│   ├── read_sensor.py
│   ├── retractable.py
│   ├── sample_daily_context.json
│   ├── smartfarmkorea_datamart.py
│   └── switch.py
├── libsbapi/
│   ├── __init__.py
│   ├── berrynext.py
│   ├── client.py
│   ├── constants.py
│   ├── daily_context_builder.py
│   ├── daily_context_io.py
│   ├── datamart.py
│   ├── farmwork.py
│   ├── greenhouse_models.py
│   ├── greenhouse_rule_helpers.py
│   ├── greenhouse_simulator.py
│   ├── ksconstants.py
│   ├── parser.py
│   ├── simulation_runner.py
│   ├── utils.py
│   └── xlsx_reader.py
├── outputs/
│   ├── daily_contexts/
│   └── recommendation_logs/
├── requirements.txt
└── tests/
    ├── test_berrynext.py
    ├── test_build_daily_context.py
    ├── test_client.py
    ├── test_daily_context_builder.py
    ├── test_datamart.py
    ├── test_farmwork.py
    ├── test_greenhouse_simulator.py
    ├── test_greenhouse_simulator_paper_rules.py
    ├── test_parser.py
    └── test_simulation_runner.py
```

Notes:

- The repository contains no `.ipynb` notebooks.
- Current GAM notebook work is outside this repository, including `/home/jungsu0327/notebookaaa758c805 (1).ipynb` and `/home/jungsu0327/gam_outputs`.
- `outputs/` contains generated daily context JSON files and recommendation logs.
- The worktree was already dirty before this audit. Existing modified/untracked source and test files were not changed by this audit.

## Current Main Modules

### API and Device Layer

- `libsbapi/client.py`: original Smart Agriculture competition API / Modbus-like client.
- `libsbapi/constants.py`, `libsbapi/ksconstants.py`, `libsbapi/utils.py`, `libsbapi/parser.py`: low-level constants, bit/word helpers, and optional parser support.
- `examples/read_sensor.py`, `examples/control_priv.py`, `examples/switch.py`, `examples/retractable.py`, `examples/nutsupply.py`: hardware/API examples for sensor reads, control authority, switches, retractables, and nutrient supply.

### SmartFarmKorea Data Loading

- `libsbapi/datamart.py`: REST client for SmartFarmKorea Open API and Data Mart services.
- `examples/smartfarmkorea_datamart.py`: example entry point for the Data Mart client.
- `README_DATAMART_KO.md`: documents service key setup and API methods.

### Local Excel to Daily Context Pipeline

- `libsbapi/xlsx_reader.py`: minimal `.xlsx` reader using zip/XML parsing.
- `libsbapi/daily_context_builder.py`: aggregates local `electric` and `pellet` farm Excel files into daily `FarmWorkContext` records.
- `libsbapi/daily_context_io.py`: writes daily context JSON files and JSONL recommendation logs.
- `examples/build_daily_context.py`: parses a normalized daily JSON file and runs the daily work engine.
- `examples/build_daily_context_from_excel.py`: builds contexts and recommendation logs from local Excel directories.
- `examples/sample_daily_context.json`: normalized example input.
- `DAILY_CONTEXT_SCHEMA_KO.md`: documents the daily context and recommendation log schema.

### Decision Engines

- `libsbapi/berrynext.py`: transparent rule-based MVP recommendation layer for irrigation, disease risk, and harvest timing.
- `libsbapi/farmwork.py`: daily work planner that combines growth stage, greenhouse snapshot, image/proxy signals, and work-history fields into ranked tasks for irrigation, disease control/scouting, harvest, and leaf pruning.
- `examples/berrynext_decision.py`, `examples/daily_farmwork.py`: runnable examples for the decision engines.

### Rule-Based Simulation

- `libsbapi/greenhouse_models.py`: dataclasses and enums for greenhouse state, environment, work actions, evidence tags, and simulation steps.
- `libsbapi/greenhouse_rule_helpers.py`: literature/manual-style rule helpers for irrigation, EC, disease pressure, harvest coloring, defoliation, evidence tags, warnings, and confidence.
- `libsbapi/greenhouse_simulator.py`: applies irrigation, disease control, harvest, leaf pruning, and runner removal actions to a greenhouse state.
- `libsbapi/simulation_runner.py`: runs multi-day scenarios, ambient drift, scenario comparison, confidence aggregation, and evidence logs.
- `examples/greenhouse_simulator.py`, `examples/greenhouse_scenario_compare.py`: runnable simulation examples.
- `dashboard/greenhouse_dashboard.py`: Streamlit dashboard for scenario controls, metrics, charts, and evidence tables.

### Tests

- `tests/test_berrynext.py`: VPD and MVP recommendation ranking/irrigation/harvest behavior.
- `tests/test_farmwork.py`: daily work planning and recent leaf-pruning suppression.
- `tests/test_build_daily_context.py`, `tests/test_daily_context_builder.py`: JSON and Excel-to-context pipeline tests.
- `tests/test_greenhouse_simulator.py`, `tests/test_greenhouse_simulator_paper_rules.py`: greenhouse action simulation and paper-rule evidence/warning behavior.
- `tests/test_simulation_runner.py`: multi-day scenario simulation and comparison.
- `tests/test_datamart.py`, `tests/test_client.py`, `tests/test_parser.py`: API client and parser boundary tests.

## Current Implemented Features

### Implemented Decision-Support Features

- Rule-based VPD calculation from temperature and humidity.
- Rule-based irrigation recommendation using root-zone moisture, VPD, solar radiation, EC, and pH.
- Rule-based disease risk recommendation using humidity, VPD, rain, ventilation, fogging, and image disease-spot proxy.
- Rule-based harvest recommendation using ripe-fruit ratio, fruit size, fruit count, rain, and high temperature.
- Daily task ranking for irrigation, disease control/scouting, harvest, and leaf pruning.
- Work-history inputs for scouting, disease control, harvest, and leaf pruning intervals.
- Safeguards in recommendations, for example avoiding extra irrigation when root zone is over-wet and avoiding repeated defoliation too soon.
- Data source labels in daily plans: growth stage, greenhouse environment, image/scouting, and work history.

### Implemented Data Features

- SmartFarmKorea REST client with path-style URL construction and API error handling.
- Local Excel reader for simple `.xlsx` files.
- Daily context builder for `electric` and `pellet` farm folders.
- Daily aggregation for temperature, humidity, CO2, solar radiation, root-zone moisture, EC, pH, rain proxy, vent opening, growth stage, fruit count, leaf density proxy, and scouting interval.
- JSON context writer and JSONL recommendation log writer.

### Implemented Rule/Simulation Features

- Greenhouse state simulation for irrigation, disease control, harvest, leaf pruning, and runner removal.
- Evidence tags for irrigation transpiration, solar/moisture triggers, VWC sensor, EC/drainage, Seolhyang EC, Botrytis flowering pressure, disease advisory, harvest coloring, runner removal, and defoliation limits.
- Warning and confidence outputs for rule-based simulation.
- Multi-day scenario comparison with ambient drift.
- Streamlit dashboard for interactive simulation scenarios.

### Implemented Documentation

- High-level BerryNext AI direction and MVP scope.
- Data-room and dataset mapping docs for local strawberry data.
- SmartFarmKorea Data Mart client docs.
- Daily context schema docs.
- Dashboard design system docs.

## Existing Files by Requested Topic

### GAM Modeling

Implemented in repository: none.

Related external work:

- `/home/jungsu0327/notebookaaa758c805 (1).ipynb`
- `/home/jungsu0327/gam_outputs`

The repository currently has no GAM training module, model artifact loader, prediction interface, GAM metrics registry, or tests for GAM predictions.

### Rule-Based Decisions

- `libsbapi/berrynext.py`
- `libsbapi/farmwork.py`
- `libsbapi/greenhouse_rule_helpers.py`
- `libsbapi/greenhouse_simulator.py`
- `libsbapi/simulation_runner.py`
- `tests/test_berrynext.py`
- `tests/test_farmwork.py`
- `tests/test_greenhouse_simulator.py`
- `tests/test_greenhouse_simulator_paper_rules.py`
- `tests/test_simulation_runner.py`

### Irrigation

- `libsbapi/berrynext.py`: `IrrigationDecisionEngine`.
- `libsbapi/greenhouse_models.py`: `IrrigationWork`.
- `libsbapi/greenhouse_rule_helpers.py`: irrigation notes, warnings, evidence, solar/moisture trigger, EC warnings.
- `libsbapi/greenhouse_simulator.py`: `_apply_irrigation`.
- `examples/nutsupply.py`: nutrient supply / irrigation actuator example.
- `tests/test_berrynext.py`, `tests/test_greenhouse_simulator.py`, `tests/test_greenhouse_simulator_paper_rules.py`.

### EC/pH

- `libsbapi/berrynext.py`: EC and pH influence irrigation recommendation.
- `libsbapi/daily_context_builder.py`: daily EC and pH aggregation from 배액/토양 columns.
- `libsbapi/greenhouse_models.py`: `drain_ec`, `feed_ec`, `drainage_ratio_pct`.
- `libsbapi/greenhouse_rule_helpers.py`: EC/drainage warnings and Seolhyang feed EC candidate range.
- `examples/nutsupply.py`: reads and sends EC/pH values to nutrient supply command example.

### Disease Risk

- `libsbapi/berrynext.py`: `DiseaseRiskDecisionEngine`.
- `libsbapi/farmwork.py`: disease recommendation boosted by scouting gap and disease-control interval.
- `libsbapi/greenhouse_rule_helpers.py`: disease pressure, Botrytis flowering/wet-canopy pressure, disease control effectiveness.
- `libsbapi/greenhouse_simulator.py`: `_apply_disease_control`.
- `tests/test_farmwork.py`, `tests/test_greenhouse_simulator.py`, `tests/test_greenhouse_simulator_paper_rules.py`.

### Harvest

- `libsbapi/berrynext.py`: `HarvestDecisionEngine`.
- `libsbapi/farmwork.py`: harvest recommendation boosted by growth stage and harvest interval.
- `libsbapi/greenhouse_models.py`: `HarvestWork`, `DistributionType`.
- `libsbapi/greenhouse_rule_helpers.py`: coloring threshold, expected days to 100 percent coloring, harvest delay pressure.
- `libsbapi/greenhouse_simulator.py`: `_apply_harvest`.
- `tests/test_berrynext.py`, `tests/test_farmwork.py`, `tests/test_greenhouse_simulator.py`, `tests/test_greenhouse_simulator_paper_rules.py`.

### Leaf Removal / Leaf Pruning

- `libsbapi/farmwork.py`: leaf-pruning daily task score and recent-work suppression.
- `libsbapi/greenhouse_models.py`: `LeafPruningWork`, `RunnerRemovalWork`.
- `libsbapi/greenhouse_rule_helpers.py`: defoliation excessive check.
- `libsbapi/greenhouse_simulator.py`: `_apply_leaf_pruning`, `_apply_runner_removal`.
- `tests/test_farmwork.py`, `tests/test_greenhouse_simulator.py`, `tests/test_greenhouse_simulator_paper_rules.py`.

### Simulation

- `libsbapi/greenhouse_models.py`
- `libsbapi/greenhouse_rule_helpers.py`
- `libsbapi/greenhouse_simulator.py`
- `libsbapi/simulation_runner.py`
- `examples/greenhouse_simulator.py`
- `examples/greenhouse_scenario_compare.py`
- `dashboard/greenhouse_dashboard.py`
- `tests/test_greenhouse_simulator.py`
- `tests/test_greenhouse_simulator_paper_rules.py`
- `tests/test_simulation_runner.py`

## Missing Pieces

### GAM and Short-Term Prediction

- No repository module trains or serves GAM models.
- No `pygam`, `sklearn`, `pandas`, or notebook dependencies are declared in `requirements.txt`.
- No short-term 1-3 hour prediction API exists.
- Existing daily context pipeline is daily aggregation, not hourly prediction.
- No model artifact format, registry, versioning, or metrics metadata exists.
- No interface connects model predictions into `DailyFarmWorkDecisionEngine` or `GreenhouseSimulator`.

### Confidence Gates and Safety Constraints

- Later implementation added `RecommendationResult` safety fields, model confidence gates, and explicit decision-support warnings.
- Remaining gap: there is still no central safety policy object for blocking or downgrading recommendations when sensor data are stale, unit-ambiguous, or operationally unsafe.
- Actuator examples still exist separately from the recommendation modules, so demos and docs must keep stating that recommendations are not direct control commands.

### Farm Work History

- `FarmWorkHistory` supports recent task intervals, but the Excel builder currently fills only `days_since_scouting`.
- Actual farm work logs for irrigation, disease control, harvest, and leaf pruning are not integrated.
- There is no feedback loop comparing recommendations to actual work, yield, disease outcome, or harvest quality.

### Literature/Manual Rule Management

- Rule thresholds are hard-coded across `berrynext.py` and `greenhouse_rule_helpers.py`.
- Evidence tags exist, but there is no structured rule table with source, threshold, crop stage, unit, scope, confidence, and citation metadata.
- Some thresholds are stated as candidate/prototype values, but runtime output does not consistently expose that limitation.

### Data Quality and Units

- The daily context builder assumes selected column names and basic positive filtering.
- There is no robust unit normalization layer for EC, pH, moisture, VWC, solar radiation, or cumulative solar radiation.
- The current builder can drop zero moisture/EC values as invalid, but it does not mark the resulting sensor coverage or confidence.
- Image inputs are mostly proxy fields from growth data; real image model outputs are not integrated.

### Tests and Tooling

- Tests cover existing rule behavior, but there are no tests for GAM prediction, model confidence gates, stale data, unit mismatches, or rule provenance.
- No package metadata or strict Python tooling config is present.
- Several existing Python files exceed 250 lines, including `libsbapi/client.py`, `libsbapi/utils.py`, `libsbapi/datamart.py`, `libsbapi/daily_context_builder.py`, `libsbapi/berrynext.py`, `libsbapi/farmwork.py`, `libsbapi/simulation_runner.py`, `dashboard/greenhouse_dashboard.py`, and some tests.

## Risky Assumptions

- Current recommendation scores are handcrafted and should not be presented as validated agronomic or autonomous-control decisions.
- Current daily aggregation can hide within-day irrigation, VPD, and solar dynamics that matter for 1-3 hour work decisions.
- `root_zone_moisture_pct` is treated as a percentage in recommendation logic, but source data may be missing, zero-filled, or unit-ambiguous.
- EC thresholds are hard-coded in multiple places and are not stage/farm calibrated.
- Disease risk uses proxy signals; it is not a validated disease incidence model.
- Harvest and leaf-pruning recommendations rely on proxy image/growth fields, not actual image inference.
- Generated `outputs/` files may be mistaken for source data or validated results.
- Existing actuator examples can write commands, but the decision-support layer does not enforce a hard separation from control execution.
- Current local GAM notebook results should not be claimed as production repository functionality until code, dependencies, metrics, and tests are moved into the repo.

## Recommended Implementation Order

1. Add a formal decision-support contract.
   - Define that outputs are recommendations with reasons, confidence, and safeguards, not direct actuator commands.
   - Add a clear output field such as `mode="decision_support"` or `requires_human_review=True`.

2. Add data quality and unit metadata to daily/hourly inputs.
   - Track missingness, stale data, source columns, unit assumptions, and sensor coverage.
   - Start with moisture, EC, pH, VPD, solar radiation, humidity, and control logs.

3. Extract rule thresholds into structured rule configuration.
   - Include rule id, source label, crop stage, variable, threshold, unit, action, confidence, and citation/note.
   - Keep existing rules, but move hard-coded values behind a documented layer.

4. Add a prediction interface before adding GAM internals.
   - Define model-independent inputs and outputs for short-term state deltas.
   - Include horizon, target variable, prediction, confidence, training rows, metric summary, and fallback reason.

5. Move GAM work into repository behind the prediction interface.
   - Start with a separate module for training/evaluation or loading notebook-exported metrics.
   - Do not connect weak predictions directly to high-priority actions without confidence gates.

6. Integrate work history beyond scouting.
   - Add parsers/fields for actual irrigation, disease control, harvest, and leaf pruning logs.
   - Use history first as safety spacing and explanation, not as supervised labels unless labels are reliable.

7. Connect predictions to recommendation scoring conservatively.
   - Let rules remain primary.
   - Use GAM deltas to adjust future-state checks only when data quality and model confidence pass gates.

8. Expand tests around safety behavior.
   - Add cases for missing moisture, stale EC, low model R2, low training rows, conflicting sensor units, and human-review downgrade.

## Files To Edit In Next Steps

Recommended first edit set:

- `libsbapi/farmwork.py`: add recommendation confidence/human-review fields and centralize daily task output semantics.
- `libsbapi/berrynext.py`: add data-quality-aware recommendation inputs or accept a separate quality/prediction context.
- `libsbapi/daily_context_builder.py`: attach sensor coverage and unit/source metadata while building contexts.
- `libsbapi/daily_context_io.py`: persist confidence, safeguards, source metadata, and decision-support disclaimers in JSON/JSONL.
- `libsbapi/greenhouse_rule_helpers.py`: prepare extraction of hard-coded thresholds into rule metadata.
- `DAILY_CONTEXT_SCHEMA_KO.md`: update schema once confidence, quality, and prediction fields are added.
- `tests/test_farmwork.py`, `tests/test_berrynext.py`, `tests/test_daily_context_builder.py`: lock the decision-support and safety-gate behavior.

Recommended second edit set:

- New `libsbapi/prediction_models.py` or `libsbapi/state_prediction.py`: model-independent prediction contracts.
- New `libsbapi/rule_config.py`: structured rule criteria and evidence metadata.
- New tests for prediction gating and rule provenance.
- Optional later: move the current external GAM notebook into `notebooks/` or replace it with a script under `examples/` once dependencies and runtime expectations are clear.

## Bottom Line

Implemented today: a rule-first strawberry decision-support prototype with daily context building, task ranking, paper-rule simulation, scenario comparison, a Streamlit simulation dashboard, and tests for existing rule behavior.

Not implemented today: repository-integrated GAM modeling, validated short-term prediction, formal confidence gates for model use, actual farm work-history ingestion beyond scouting, structured literature rule metadata, and a runtime contract that fully prevents autonomous-controller overclaiming.

## Follow-up Direction Note

Follow-up date: 2026-06-25

The project direction has been corrected after this audit. BerryNext should now be described as an explainable strawberry greenhouse decision-support system, not as a supervised farmwork-history learning system and not as an autonomous greenhouse controller.

The fixed Level 1 management actions are:

- irrigation
- EC / nutrient solution adjustment
- ventilation
- shading
- heat preservation / heating review

Disease-risk scouting, harvest possibility, and leaf-removal review are Level 2 auxiliary alerts only. They must not be presented as validated disease, harvest, or leaf-removal prediction systems unless explicit local labels, validation results, and tests are added.

Work history, when available, is used only for safety spacing, cooldown intervals, and explanation. It is not a supervised label source. Scenario simulation compares candidate action directions and must not be used to fabricate fake labels for supervised training.

The intended architecture is:

```text
Sensor Data
→ Current State Builder
→ Environmental Predictor
→ Scenario Simulator
→ Threshold / Literature Rule Engine
→ Work-Need Scorer
→ Recommendation Generator
```

GAM belongs in the Environmental Predictor stage as a short-term environmental delta predictor. Predictor maturity should progress from v0 no-change baseline, v1 rolling delta baseline, v2 linear regression, v3 GAM, then v4 LSTM or Transformer only if data volume and validation justify it.
