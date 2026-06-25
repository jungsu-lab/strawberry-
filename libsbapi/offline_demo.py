from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Final

from .auxiliary_alert_scoring import auxiliary_alert_scores
from .current_state_builder import CurrentStateBuilder
from .decision_contract import CoreRecommendation, CurrentGreenhouseState, WorkNeedScore
from .environmental_prediction import NoChangeBaselinePredictor, predict_environment_delta
from .evidence_rules import EvidenceRule, auxiliary_alert_rules, core_level1_rules, load_evidence_rules
from .greenhouse_models import GreenhouseEnvironment, GreenhouseState
from .recommendation_generator import ACTION_LABELS_KO, RecommendationGenerator, RecommendationReport
from .scenario_comparison import ShortHorizonScenarioComparison, compare_action_candidates
from .work_need_scorer import WorkNeedScorer


SAMPLE_CONTEXT: Final = Path(__file__).resolve().parents[1] / "examples" / "sample_daily_context.json"
AUXILIARY_ACTION_LABELS: Final = {
    "disease_environment_risk_proxy": "disease-risk scouting alert",
    "harvest_monitoring": "harvest possibility alert",
    "leaf_removal_caution": "leaf-removal review alert",
}


@dataclass(frozen=True, slots=True)
class BerryNextOfflineDemo:
    current_state: CurrentGreenhouseState
    predictions: tuple
    scenario_report: ShortHorizonScenarioComparison
    evidence_rules: tuple[EvidenceRule, ...]
    work_scores: tuple[WorkNeedScore, ...]
    auxiliary_scores: tuple[WorkNeedScore, ...]
    recommendation_report: RecommendationReport


def build_demo(context_path: Path = SAMPLE_CONTEXT) -> BerryNextOfflineDemo:
    current_state = CurrentStateBuilder().from_daily_context_file(context_path)
    context_payload = _load_context_payload(context_path)
    predictions = predict_environment_delta(
        current_state,
        predictor=NoChangeBaselinePredictor(),
        horizons=(1, 2, 3),
    )
    scenario_report = compare_action_candidates(
        _greenhouse_state_from_current(current_state),
        _environment_from_current(current_state),
        horizon_hours=3,
    )
    evidence_rules = load_evidence_rules()
    work_scores = WorkNeedScorer(evidence_rules).score(current_state, predictions)
    auxiliary_scores = auxiliary_alert_scores(current_state, context_payload)
    recommendation_report = RecommendationGenerator().generate(
        work_need_scores=work_scores,
        predictions=predictions,
        scenario_results=scenario_report.scenarios,
        auxiliary_alerts=auxiliary_scores,
        evidence_rules=evidence_rules,
    )
    return BerryNextOfflineDemo(
        current_state=current_state,
        predictions=predictions,
        scenario_report=scenario_report,
        evidence_rules=evidence_rules,
        work_scores=work_scores,
        auxiliary_scores=auxiliary_scores,
        recommendation_report=recommendation_report,
    )


def format_demo(demo: BerryNextOfflineDemo) -> str:
    lines = [
        "BerryNext offline decision-support demo",
        "sample context -> current state -> baseline environmental prediction -> scenario comparison",
        "-> literature/manual rule checks -> work-need scores -> recommendations",
        "",
        "mode: decision_support; human review required before any greenhouse action.",
        "GAM planned/future: current demo uses v0 no-change baseline prediction only.",
        "",
        "1. Current state",
        _state_line(demo.current_state),
        "",
        "2. Predicted future state",
        *(_prediction_lines(demo.predictions)),
        "",
        "3. Scenario comparison summary",
        demo.scenario_report.not_training_label_notice,
        *(_scenario_lines(demo.scenario_report)),
        "",
        "4. Literature/manual rule checks",
        *(_rule_lines(demo.evidence_rules)),
        "",
        "5. Work-need scores",
        *(_score_lines(demo.work_scores)),
        "",
        "6. Level 1 ranked recommendations",
        *(_recommendation_lines(demo.recommendation_report.level1_recommendations)),
        "",
        "7. Level 2 auxiliary alerts",
        *(_auxiliary_lines(demo.recommendation_report.auxiliary_alerts)),
        "",
        "JSON-like summary",
        *(_json_summary_lines(demo.recommendation_report)),
    ]
    return "\n".join(lines)


def main() -> None:
    print(format_demo(build_demo()))


def _state_line(state: CurrentGreenhouseState) -> str:
    return (
        f"- air_temp={state.air_temp}C, humidity={state.humidity}%, VPD={state.vpd}kPa, "
        f"radiation={state.solar_radiation}W/m2, root_moisture={state.root_zone_moisture}%, "
        f"drain_ec={state.drain_ec}, growth_stage={state.growth_stage}, time_of_day={state.time_of_day}"
    )


def _prediction_lines(predictions: tuple) -> list[str]:
    targets = ("air_temp", "humidity", "vpd", "solar_radiation", "root_zone_moisture", "drain_ec")
    lines: list[str] = []
    for target in targets:
        by_target = [item for item in predictions if item.target == target]
        if not by_target:
            continue
        horizon_text = ", ".join(
            f"{item.horizon_hours}h={item.predicted_value} ({item.predicted_delta:+.2f})"
            for item in by_target
        )
        model = by_target[0].model_used
        fallback = "fallback" if by_target[0].fallback_used else "model"
        lines.append(f"- {target}: {horizon_text}; {model}/{fallback}; confidence={by_target[0].confidence:.2f}")
    return lines


def _scenario_lines(report: ShortHorizonScenarioComparison) -> list[str]:
    ranked = sorted(
        report.scenarios,
        key=lambda item: (
            abs(item.moisture_delta)
            + abs(item.ec_delta)
            + abs(item.humidity_delta)
            + abs(item.temperature_delta)
            + abs(item.energy_cost_delta) / 10.0
        ),
        reverse=True,
    )
    return [
        (
            f"- {item.action_type}: moisture {item.moisture_delta:+.1f}, EC {item.ec_delta:+.2f}, "
            f"humidity {item.humidity_delta:+.1f}, VPD {item.vpd_delta:+.2f}, "
            f"temp {item.temperature_delta:+.1f}, energy {item.energy_cost_delta:+.1f}, "
            f"confidence={item.confidence:.2f}"
        )
        for item in ranked[:6]
    ]


def _rule_lines(rules: tuple[EvidenceRule, ...]) -> list[str]:
    core_actions = {rule.action_type for rule in core_level1_rules(rules)}
    auxiliary_actions = {rule.action_type for rule in auxiliary_alert_rules(rules)}
    return [
        f"- Level 1 rule actions: {', '.join(sorted(core_actions))}",
        f"- Level 2 auxiliary rule actions: {', '.join(sorted(auxiliary_actions))}",
        "- Rule thresholds are provisional literature/manual or prototype rules and need local calibration.",
    ]


def _score_lines(scores: tuple[WorkNeedScore, ...]) -> list[str]:
    return [
        (
            f"- {ACTION_LABELS_KO.get(score.action_type, score.action_type)}: "
            f"score={score.score:.0f}, status={score.status}, confidence={score.confidence:.2f}, "
            f"components={score.components}"
        )
        for score in scores
    ]


def _recommendation_lines(recommendations: tuple[CoreRecommendation, ...]) -> list[str]:
    return [
        (
            f"- {rank}순위 {ACTION_LABELS_KO.get(item.action, item.action)}: "
            f"{item.score:.0f}점/{item.status}, confidence=human-reviewed, "
            f"reason={'; '.join(item.reasons[:2])}"
        )
        for rank, item in enumerate(recommendations, start=1)
    ]


def _auxiliary_lines(alerts: tuple[CoreRecommendation, ...]) -> list[str]:
    if not alerts:
        return ["- No auxiliary alerts exceeded the prototype display threshold."]
    return [
        (
            f"- {AUXILIARY_ACTION_LABELS.get(item.action, item.action)}: "
            f"{item.score:.0f}점/{item.status}; {ACTION_LABELS_KO.get(item.action, item.action)}; "
            f"reason={_auxiliary_display_reason(item.action)}"
        )
        for item in alerts
    ]


def _json_summary_lines(report: RecommendationReport) -> list[str]:
    payload = report.to_json()
    return [
        f"- title={payload['title']}",
        f"- mode={payload['mode']}",
        f"- requires_human_review={payload['requires_human_review']}",
        f"- level1_count={len(payload['level1_recommendations'])}",
        f"- auxiliary_alert_count={len(payload['auxiliary_alerts'])}",
    ]


def _auxiliary_display_reason(action_type: str) -> str:
    return {
        "disease_environment_risk_proxy": "high humidity / low VPD environmental proxy; recommend scouting with ventilation review",
        "harvest_monitoring": "growth stage and image proxies support harvest possibility monitoring",
        "leaf_removal_caution": "dense-canopy proxy and high humidity support cautious leaf-removal review",
    }.get(action_type, "auxiliary evidence is present")


def _load_context_payload(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload if isinstance(payload, dict) else {}


def _greenhouse_state_from_current(current_state: CurrentGreenhouseState) -> GreenhouseState:
    return GreenhouseState(
        substrate_moisture_pct=current_state.root_zone_moisture or 50.0,
        drain_ec=current_state.drain_ec or current_state.root_ec or 1.5,
        disease_risk=0.35,
        ripe_fruit_ratio=0.0,
        fruit_count=0,
        leaf_density=0.6,
        ventilation_score=0.4,
        yield_potential=1.0,
        marketable_yield_kg=0.0,
        quality_risk=0.1,
        feed_ec=current_state.feed_ec,
        drainage_ratio_pct=current_state.drainage_ratio,
    )


def _environment_from_current(current_state: CurrentGreenhouseState) -> GreenhouseEnvironment:
    return GreenhouseEnvironment(
        solar_radiation_w_m2=current_state.solar_radiation or 0.0,
        vpd_kpa=current_state.vpd or 0.7,
        humidity_pct=current_state.humidity or 70.0,
        rain_probability=0.0,
        inside_temperature_c=current_state.air_temp or 22.0,
    )
