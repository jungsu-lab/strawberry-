from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Final

from .auxiliary_alert_scoring import auxiliary_alert_scores
from .current_state_builder import CurrentStateBuilder
from .decision_contract import CoreRecommendation, CurrentGreenhouseState, WorkNeedScore
from .display_labels import AUXILIARY_ALERT_LABELS_KO, action_label, scenario_label, status_label, variable_label
from .environmental_prediction import NoChangeBaselinePredictor, predict_environment_delta
from .evidence_rules import EvidenceRule, auxiliary_alert_rules, core_level1_rules, load_evidence_rules
from .greenhouse_models import GreenhouseEnvironment, GreenhouseState
from .recommendation_generator import ACTION_LABELS_KO, RecommendationGenerator, RecommendationReport
from .scenario_comparison import ShortHorizonScenarioComparison, compare_action_candidates
from .work_need_scorer import WorkNeedScorer


SAMPLE_CONTEXT: Final = Path(__file__).resolve().parents[1] / "examples" / "sample_daily_context.json"
AUXILIARY_ACTION_LABELS: Final = AUXILIARY_ALERT_LABELS_KO


@dataclass(frozen=True, slots=True)
class BerryNextOfflineDemo:
    current_state: CurrentGreenhouseState
    predictions: tuple
    scenario_report: ShortHorizonScenarioComparison
    scenario_input_warnings: tuple[str, ...]
    evidence_rules: tuple[EvidenceRule, ...]
    work_scores: tuple[WorkNeedScore, ...]
    auxiliary_scores: tuple[WorkNeedScore, ...]
    recommendation_report: RecommendationReport


def build_demo(context_path: Path = SAMPLE_CONTEXT) -> BerryNextOfflineDemo:
    current_state = CurrentStateBuilder().from_daily_context_file(context_path)
    context_payload = _load_context_payload(context_path)
    return build_demo_from_current_state(current_state, context_payload=context_payload)


def build_demo_from_current_state(
    current_state: CurrentGreenhouseState,
    context_payload: dict | None = None,
) -> BerryNextOfflineDemo:
    payload = context_payload or {}
    predictions = predict_environment_delta(
        current_state,
        predictor=NoChangeBaselinePredictor(),
        horizons=(1, 2, 3),
    )
    scenario_state, scenario_environment, scenario_input_warnings = _scenario_inputs_from_current(current_state, payload)
    scenario_report = compare_action_candidates(
        scenario_state,
        scenario_environment,
        horizon_hours=3,
    )
    evidence_rules = load_evidence_rules()
    work_scores = WorkNeedScorer(evidence_rules).score(current_state, predictions)
    auxiliary_scores = auxiliary_alert_scores(current_state, payload)
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
        scenario_input_warnings=scenario_input_warnings,
        evidence_rules=evidence_rules,
        work_scores=work_scores,
        auxiliary_scores=auxiliary_scores,
        recommendation_report=recommendation_report,
    )


def format_demo(demo: BerryNextOfflineDemo) -> str:
    lines = [
        "BerryNext 오프라인 의사결정 보조 데모",
        "샘플 context -> 현재 상태 -> 기준선 환경 예측 -> 시나리오 비교",
        "-> 문헌/매뉴얼 기준 룰 확인 -> 필요도 점수 -> 추천",
        "",
        "mode: decision_support; 실제 작업 전 사람 검토가 필요합니다.",
        "GAM은 향후 단기 환경 변화량 예측기로 계획되어 있으며, 현재 데모는 v0 no-change 기준선 예측만 사용합니다.",
        "",
        "1. 현재 상태",
        _state_line(demo.current_state),
        "",
        "2. 1~3시간 예상 상태",
        *(_prediction_lines(demo.predictions)),
        "",
        "3. 시나리오 비교 요약",
        demo.scenario_report.not_training_label_notice,
        *(_scenario_input_warning_lines(demo.scenario_input_warnings)),
        *(_scenario_lines(demo.scenario_report)),
        "",
        "4. 문헌/매뉴얼 기준 룰 확인",
        *(_rule_lines(demo.evidence_rules)),
        "",
        "5. 필요도 점수",
        *(_score_lines(demo.work_scores)),
        "",
        "6. Level 1 작업 추천 순위",
        *(_recommendation_lines(demo.recommendation_report.level1_recommendations)),
        "",
        "7. Level 2 보조 알림",
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
        f"- 내부 온도={state.air_temp}℃, 습도={state.humidity}%, VPD={state.vpd}kPa, "
        f"일사량={state.solar_radiation}W/m², 근권수분={state.root_zone_moisture}%, "
        f"배액 EC={state.drain_ec}, 생육 단계={state.growth_stage}, 시간대={state.time_of_day}"
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
        fallback = "기준선/대체 예측" if by_target[0].fallback_used else "모델 예측"
        lines.append(f"- {variable_label(target)} ({target}): {horizon_text}; {model}/{fallback}; 신뢰도={by_target[0].confidence:.2f}")
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
            f"- {scenario_label(item.action_type)} ({item.action_type}): 수분 {item.moisture_delta:+.1f}, EC {item.ec_delta:+.2f}, "
            f"습도 {item.humidity_delta:+.1f}, VPD {item.vpd_delta:+.2f}, "
            f"온도 {item.temperature_delta:+.1f}, 에너지 {item.energy_cost_delta:+.1f}, "
            f"confidence={item.confidence:.2f}"
        )
        for item in ranked[:6]
    ]


def _scenario_input_warning_lines(warnings: tuple[str, ...]) -> list[str]:
    if not warnings:
        return []
    return ["- 시나리오 입력 대체값 경고: " + " / ".join(warnings)]


def _rule_lines(rules: tuple[EvidenceRule, ...]) -> list[str]:
    core_actions = {rule.action_type for rule in core_level1_rules(rules)}
    auxiliary_actions = {rule.action_type for rule in auxiliary_alert_rules(rules)}
    return [
        f"- Level 1 룰 작업: {', '.join(action_label(action) for action in sorted(core_actions))}",
        f"- Level 2 보조 알림 룰: {', '.join(action_label(action) for action in sorted(auxiliary_actions))}",
        "- 현재 임계값은 문헌/매뉴얼 또는 prototype 룰이며 농가별 보정이 필요합니다.",
    ]


def _score_lines(scores: tuple[WorkNeedScore, ...]) -> list[str]:
    return [
        (
            f"- {ACTION_LABELS_KO.get(score.action_type, score.action_type)}: "
            f"필요도={score.score:.0f}, 상태={status_label(score.status)}, 신뢰도={score.confidence:.2f}, "
            f"components={score.components}"
        )
        for score in scores
    ]


def _recommendation_lines(recommendations: tuple[CoreRecommendation, ...]) -> list[str]:
    return [
        (
            f"- {rank}순위 {ACTION_LABELS_KO.get(item.action, item.action)}: "
            f"{item.score:.0f}점/{status_label(item.status)}, 사람 검토 필요, "
            f"이유={'; '.join(item.reasons[:2])}"
        )
        for rank, item in enumerate(recommendations, start=1)
    ]


def _auxiliary_lines(alerts: tuple[CoreRecommendation, ...]) -> list[str]:
    if not alerts:
        return ["- 표시 임계값을 넘은 보조 알림이 없습니다."]
    return [
        (
            f"- {AUXILIARY_ACTION_LABELS.get(item.action, item.action)}: "
            f"{item.score:.0f}점/{status_label(item.status)}; {ACTION_LABELS_KO.get(item.action, item.action)}; "
            f"이유={_auxiliary_display_reason(item.action)}"
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
        "disease_environment_risk_proxy": "고습·저VPD 기반 병해 환경 위험 프록시입니다. 환기 검토와 함께 예찰을 권장합니다.",
        "harvest_monitoring": "생육 단계와 이미지 프록시가 수확 가능성 확인을 뒷받침합니다.",
        "leaf_removal_caution": "엽밀도 프록시와 고습 조건이 있어 보수적인 적엽 검토가 필요할 수 있습니다.",
    }.get(action_type, "보조 확인 근거가 있습니다.")


def _load_context_payload(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload if isinstance(payload, dict) else {}


def _scenario_inputs_from_current(
    current_state: CurrentGreenhouseState,
    context_payload: dict | None = None,
) -> tuple[GreenhouseState, GreenhouseEnvironment, tuple[str, ...]]:
    payload = context_payload or {}
    greenhouse_state, state_warnings = _greenhouse_state_from_current_with_warnings(current_state, payload)
    environment, environment_warnings = _environment_from_current_with_warnings(current_state, payload)
    return greenhouse_state, environment, (*state_warnings, *environment_warnings)


def _greenhouse_state_from_current(current_state: CurrentGreenhouseState) -> GreenhouseState:
    greenhouse_state, _ = _greenhouse_state_from_current_with_warnings(current_state, {})
    return greenhouse_state


def _greenhouse_state_from_current_with_warnings(
    current_state: CurrentGreenhouseState,
    context_payload: dict,
) -> tuple[GreenhouseState, tuple[str, ...]]:
    snapshot = _object(context_payload.get("snapshot", {}))
    image = _object(snapshot.get("image", {}))
    warnings: list[str] = []

    disease_risk = _first_not_none(_float_from_mapping(image, "disease_spot_ratio"), 0.0)
    if "disease_spot_ratio" not in image:
        warnings.append("scenario disease_risk uses prototype placeholder because image disease proxy is missing")
    ripe_fruit_ratio = _first_not_none(_float_from_mapping(image, "ripe_fruit_ratio"), 0.0)
    if "ripe_fruit_ratio" not in image:
        warnings.append("scenario ripe_fruit_ratio uses prototype placeholder because image ripeness proxy is missing")
    fruit_count = int(_first_not_none(_float_from_mapping(image, "fruit_count"), 0.0))
    if "fruit_count" not in image:
        warnings.append("scenario fruit_count uses prototype placeholder because image fruit count is missing")
    leaf_density = _first_not_none(_float_from_mapping(image, "leaf_density"), 0.6)
    if "leaf_density" not in image:
        warnings.append("scenario leaf_density uses prototype placeholder because canopy proxy is missing")
    ventilation_score = _float_from_mapping(snapshot, "vent_open_pct")
    if ventilation_score is None:
        ventilation_score = 0.4
        warnings.append("scenario ventilation_score uses prototype placeholder because vent opening is missing")
    else:
        ventilation_score = max(0.0, min(ventilation_score / 100.0, 1.0))
    warnings.append("scenario yield_potential uses prototype placeholder; not used for Level 1 ranking")
    warnings.append("scenario quality_risk uses prototype placeholder; not used for Level 1 ranking")

    return GreenhouseState(
        substrate_moisture_pct=_first_not_none(current_state.root_zone_moisture, current_state.substrate_moisture, 50.0),
        drain_ec=_first_not_none(current_state.drain_ec, current_state.root_ec, 1.5),
        disease_risk=disease_risk,
        ripe_fruit_ratio=ripe_fruit_ratio,
        fruit_count=fruit_count,
        leaf_density=leaf_density,
        ventilation_score=ventilation_score,
        yield_potential=1.0,
        marketable_yield_kg=0.0,
        quality_risk=0.1,
        feed_ec=current_state.feed_ec,
        drainage_ratio_pct=current_state.drainage_ratio,
    ), tuple(warnings)


def _environment_from_current(current_state: CurrentGreenhouseState) -> GreenhouseEnvironment:
    environment, _ = _environment_from_current_with_warnings(current_state, {})
    return environment


def _environment_from_current_with_warnings(
    current_state: CurrentGreenhouseState,
    context_payload: dict,
) -> tuple[GreenhouseEnvironment, tuple[str, ...]]:
    snapshot = _object(context_payload.get("snapshot", {}))
    weather = _object(snapshot.get("weather", {}))
    warnings: list[str] = []
    rain_probability = _float_from_mapping(weather, "rain_probability")
    if rain_probability is None:
        rain_probability = 0.0
        warnings.append("scenario rain_probability uses prototype placeholder because weather rain probability is missing")
    return GreenhouseEnvironment(
        solar_radiation_w_m2=_first_not_none(current_state.solar_radiation, 0.0),
        vpd_kpa=_first_not_none(current_state.vpd, 0.7),
        humidity_pct=_first_not_none(current_state.humidity, 70.0),
        rain_probability=rain_probability,
        inside_temperature_c=_first_not_none(current_state.air_temp, 22.0),
    ), tuple(warnings)


def _object(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _float_from_mapping(data: dict, key: str) -> float | None:
    value = data.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _first_not_none(*values: float | None) -> float:
    for value in values:
        if value is not None:
            return value
    raise ValueError("at least one fallback value is required")
