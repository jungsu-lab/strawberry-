# Demo Scenarios

Realistic demo inputs live under `examples/scenarios/`.

The current set covers:

- high VPD plus low substrate moisture for irrigation check
- high humidity plus low VPD for ventilation/dehumidification and disease environmental risk proxy
- high root-zone or drainage EC for nutrient/EC check
- low night temperature for heating or thermal protection
- dense canopy with recent leaf work for conservative leaf removal caution

Run all demos:

```bash
python3 scripts/run_demo_scenarios.py
```

Outputs are written to `artifacts/demo_outputs/`:

- one JSON result per scenario
- `summary.json`
- `demo_report.md`

The reports use directional language and include rule-based assumptions, evidence references, safety flags, and warnings. The what-if section is not a validated causal simulation and does not issue greenhouse control commands.
