#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
# How to run:
# python3 scripts/run_demo_scenarios.py

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Final


REPO_ROOT: Final = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libsbapi.action_recommenders import ActionRecommendationEngine
from libsbapi.decision_contract import RecommendationResult
from libsbapi.decision_contract_io import (
    JsonObject,
    JsonValue,
    greenhouse_snapshot_from_json,
    prediction_result_from_json,
)
from libsbapi.evidence_rules import load_evidence_rules
from libsbapi.scenario_simulator import (
    ScenarioAction,
    ScenarioCandidate,
    ScenarioSimulationReport,
    ScenarioSimulationRequest,
    simulate_scenarios,
)
from libsbapi.scenario_simulator_io import (
    scenario_report_to_json,
    scenario_result_to_json,
)


DEFAULT_SCENARIO_DIR: Final = REPO_ROOT / "examples" / "scenarios"
DEFAULT_OUTPUT_DIR: Final = REPO_ROOT / "artifacts" / "demo_outputs"
SCENARIO_ACTIONS_BY_VALUE: Final[dict[str, ScenarioAction]] = {
    "irrigation": "irrigation",
    "ventilation_dehumidification": "ventilation_dehumidification",
    "shading_high_temperature": "shading_high_temperature",
    "heating_low_temperature": "heating_low_temperature",
    "nutrient_ec_check": "nutrient_ec_check",
    "no_action": "no_action",
}


@dataclass(frozen=True, slots=True)
class DemoScenario:
    input_path: Path
    scenario_id: str
    title: str
    expected_focus_action: str
    snapshot: JsonObject
    candidate_actions: tuple[str, ...]
    predictions: tuple[JsonObject, ...]


@dataclass(frozen=True, slots=True)
class DemoScenarioReport:
    input_path: Path
    scenario: DemoScenario
    recommendations: tuple[RecommendationResult, ...]
    auxiliary_alerts: tuple[RecommendationResult, ...]
    scenario_simulation: ScenarioSimulationReport


@dataclass(frozen=True, slots=True)
class DemoRunResult:
    output_dir: Path
    scenario_reports: tuple[DemoScenarioReport, ...]


def run_demo_scenarios(
    scenario_dir: Path = DEFAULT_SCENARIO_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> DemoRunResult:
    evidence_rules = load_evidence_rules()
    output_dir.mkdir(parents=True, exist_ok=True)
    reports: list[DemoScenarioReport] = []
    for scenario_path in sorted(scenario_dir.glob("*.json")):
        scenario = load_demo_scenario(scenario_path)
        snapshot = greenhouse_snapshot_from_json(scenario.snapshot)
        predictions = tuple(prediction_result_from_json(item) for item in scenario.predictions)
        engine = ActionRecommendationEngine(evidence_rules)
        recommendations = engine.recommend(snapshot, predictions)
        auxiliary_alerts = engine.auxiliary_alerts(snapshot, predictions)
        simulation = simulate_scenarios(
            ScenarioSimulationRequest(
                snapshot=snapshot,
                candidate_actions=tuple(
                    ScenarioCandidate(_scenario_action(action))
                    for action in scenario.candidate_actions
                ),
                evidence_rules=evidence_rules,
                predictions=predictions,
            )
        )
        report = DemoScenarioReport(scenario_path, scenario, recommendations, auxiliary_alerts, simulation)
        write_scenario_output(output_dir / f"{scenario.scenario_id}.json", report)
        reports.append(report)
    result = DemoRunResult(output_dir=output_dir, scenario_reports=tuple(reports))
    write_summary_json(output_dir / "summary.json", result)
    write_markdown_report(output_dir / "demo_report.md", result)
    return result


def load_demo_scenario(path: Path) -> DemoScenario:
    with path.open(encoding="utf-8") as file:
        payload: JsonValue = json.load(file)
    data = _json_object(payload, "root")
    metadata = _json_object(data.get("scenario"), "scenario")
    return DemoScenario(
        input_path=path,
        scenario_id=_str_field(metadata, "id"),
        title=_str_field(metadata, "title"),
        expected_focus_action=_str_field(metadata, "expected_focus_action"),
        snapshot=_json_object(data.get("snapshot"), "snapshot"),
        candidate_actions=tuple(_str_list(data, "candidate_actions")),
        predictions=tuple(_json_object(item, "predictions") for item in _object_list(data, "predictions")),
    )


def write_scenario_output(path: Path, report: DemoScenarioReport) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(demo_scenario_report_to_json(report), file, ensure_ascii=False, indent=2)
        _ = file.write("\n")


def write_summary_json(path: Path, result: DemoRunResult) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(demo_run_result_to_json(result), file, ensure_ascii=False, indent=2)
        _ = file.write("\n")


def write_markdown_report(path: Path, result: DemoRunResult) -> None:
    lines = ["# Strawberry Decision-Support Demo Report", ""]
    lines.append("Rule-based assumptions and literature/manual evidence are used unless a model passes confidence gates.")
    lines.append("Scenario outputs are decision support, not validated causal simulation or control commands.")
    for report in result.scenario_reports:
        lines.extend(_markdown_section(report))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def demo_run_result_to_json(result: DemoRunResult) -> JsonObject:
    return {
        "output_dir": str(result.output_dir),
        "scenario_count": len(result.scenario_reports),
        "scenarios": [demo_scenario_report_to_json(report) for report in result.scenario_reports],
    }


def demo_scenario_report_to_json(report: DemoScenarioReport) -> JsonObject:
    return {
        "scenario_id": report.scenario.scenario_id,
        "title": report.scenario.title,
        "expected_focus_action": report.scenario.expected_focus_action,
        "input_path": str(report.input_path),
        "recommendations": [
            recommendation_to_json(item) for item in report.recommendations
        ],
        "auxiliary_alerts": [
            recommendation_to_json(item) for item in report.auxiliary_alerts
        ],
        "what_if_simulation": scenario_report_to_json(report.scenario_simulation),
    }


def recommendation_to_json(item: RecommendationResult) -> JsonObject:
    return {
        "action_type": item.action_type,
        "priority": item.priority,
        "confidence": item.confidence,
        "reason": item.reason,
        "expected_effect": item.expected_effect,
        "risks": list(item.risks),
        "evidence_references": [reference.reference_id for reference in item.evidence_references],
        "safety_flags": list(item.safety_flags),
        "model_used": item.model_used,
        "fallback_used": item.fallback_used,
    }


def _markdown_section(report: DemoScenarioReport) -> list[str]:
    top_recommendations = report.recommendations[:3]
    focus = _focus_recommendation(report)
    lines = ["", f"## {report.scenario.title}", ""]
    lines.append(f"- Expected focus: `{report.scenario.expected_focus_action}`")
    if focus is not None:
        lines.append(
            f"- Focus recommendation: `{focus.action_type}` {focus.priority} "
            f"confidence={focus.confidence}: {focus.reason}"
        )
        lines.append(f"  - Risks: {'; '.join(focus.risks)}")
        lines.append(f"  - Safety: {', '.join(focus.safety_flags)}")
    lines.append("- Full ranking highlights:")
    for item in top_recommendations:
        lines.append(
            f"  - `{item.action_type}` {item.priority} confidence={item.confidence}: {item.reason}"
        )
        lines.append(f"    - Risks: {'; '.join(item.risks)}")
        lines.append(f"    - Safety: {', '.join(item.safety_flags)}")
    if report.auxiliary_alerts:
        lines.append("- Auxiliary alerts:")
        for item in report.auxiliary_alerts:
            lines.append(
                f"  - `{item.action_type}` {item.priority} confidence={item.confidence}: {item.reason}"
            )
            lines.append(f"    - Risks: {'; '.join(item.risks)}")
            lines.append(f"    - Safety: {', '.join(item.safety_flags)}")
    lines.append("- What-if directions:")
    for scenario in report.scenario_simulation.scenarios:
        lines.append(f"  - `{scenario.action_type}`: {'; '.join(scenario.expected_state_direction)}")
        lines.append(f"    - Assumptions: {'; '.join(scenario.assumptions)}")
        lines.append(f"    - Warning: {scenario.not_validated_warning}")
    return lines


def _focus_recommendation(report: DemoScenarioReport) -> RecommendationResult | None:
    for item in report.recommendations:
        if item.action_type == report.scenario.expected_focus_action:
            return item
    for item in report.auxiliary_alerts:
        if item.action_type == report.scenario.expected_focus_action:
            return item
    return None


def _scenario_action(value: str) -> ScenarioAction:
    action = SCENARIO_ACTIONS_BY_VALUE.get(value)
    if action is not None:
        return action
    raise DemoScenarioError("candidate_actions", f"unsupported action: {value}")


@dataclass(frozen=True, slots=True)
class DemoScenarioError(ValueError):
    field_name: str
    detail: str

    def __str__(self) -> str:
        return f"{self.field_name}: {self.detail}"


def _json_object(value: JsonValue, field_name: str) -> JsonObject:
    if isinstance(value, dict):
        return value
    raise DemoScenarioError(field_name, "must be an object")


def _object_list(data: JsonObject, field_name: str) -> list[JsonValue]:
    value = data.get(field_name, [])
    if isinstance(value, list):
        return value
    raise DemoScenarioError(field_name, "must be a list")


def _str_list(data: JsonObject, field_name: str) -> list[str]:
    value = data.get(field_name, [])
    if isinstance(value, list):
        return [_str_value(item, field_name) for item in value]
    raise DemoScenarioError(field_name, "must be a list")


def _str_field(data: JsonObject, field_name: str) -> str:
    return _str_value(data.get(field_name), field_name)


def _str_value(value: JsonValue, field_name: str) -> str:
    if isinstance(value, str):
        return value
    raise DemoScenarioError(field_name, "must be a string")


def main(argv: list[str]) -> int:
    scenario_dir = Path(argv[1]) if len(argv) >= 2 else DEFAULT_SCENARIO_DIR
    output_dir = Path(argv[2]) if len(argv) >= 3 else DEFAULT_OUTPUT_DIR
    result = run_demo_scenarios(scenario_dir, output_dir)
    print(f"Wrote {len(result.scenario_reports)} demo scenario reports to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
