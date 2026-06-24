# What-If Scenario Simulator

The v0 scenario simulator lives in:

- `libsbapi/scenario_simulator.py`
- `libsbapi/scenario_simulator_io.py`
- `scripts/run_scenario_simulation.py`

It compares short-term action candidates for decision support. It is not a validated causal greenhouse simulator and does not issue control commands.

## Supported Actions

- `irrigation`
- `ventilation_dehumidification`
- `shading_high_temperature`
- `heating_low_temperature`
- `nutrient_ec_check`
- `no_action`

## Output Semantics

Each scenario returns directional language:

- `expected_state_direction`
- `potential_benefits`
- `potential_risks`
- `confidence`
- `evidence_references`
- `assumptions`
- `not_validated_warning`

The simulator intentionally avoids fake precise numbers. Optional `PredictionResult` values are first filtered by action relevance and the model confidence gate. Only relevant usable predictions can slightly adjust confidence; weak, missing, or unrelated predictions do not raise scenario confidence. The output remains directional unless a future validated model explicitly supports numeric estimates.

## CLI

Run the sample scenario comparison:

```bash
python3 scripts/run_scenario_simulation.py \
  examples/sample_scenario_simulation_input.json \
  examples/sample_scenario_simulation_output.json
```

The sample compares irrigation, ventilation/dehumidification, shading, and no action.
