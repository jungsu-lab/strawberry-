#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
# How to run:
# python3 scripts/run_scenario_simulation.py examples/sample_scenario_simulation_input.json examples/sample_scenario_simulation_output.json

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libsbapi.evidence_rules import load_evidence_rules
from libsbapi.scenario_simulator import NOT_VALIDATED_WARNING, simulate_scenarios
from libsbapi.scenario_simulator_io import (
    load_scenario_simulation_request,
    write_scenario_simulation_report,
)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: run_scenario_simulation.py <input_json> <output_json>")
        return 2

    input_path = Path(argv[1])
    output_path = Path(argv[2])
    request = load_scenario_simulation_request(input_path, load_evidence_rules())
    report = simulate_scenarios(request)
    write_scenario_simulation_report(output_path, report)
    print(NOT_VALIDATED_WARNING)
    print(f"Wrote {len(report.scenarios)} scenario estimates to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
