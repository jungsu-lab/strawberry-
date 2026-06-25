from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from .decision_contract import CoreRecommendation, PredictionResult, WorkNeedScore
from .evidence_rules import EvidenceRule, evidence_rules_by_action_type
from .prediction_targets import prediction_relates_to_action
from .scenario_comparison import ShortHorizonScenarioResult


ACTION_LABELS_KO: Final = {
    "irrigation": "관수",
    "nutrient_ec_check": "EC/양액 조정 검토",
    "ventilation_dehumidification": "환기",
    "shading_high_temperature": "차광",
    "heating_low_temperature": "보온/난방 검토",
    "disease_environment_risk_proxy": "병해 위험 예찰 알림",
    "harvest_monitoring": "수확 가능성 알림",
    "leaf_removal_caution": "적엽 검토 알림",
}
SCENARIO_ACTION_TO_LEVEL1: Final = {
    "irrigation": "irrigation",
    "no_irrigation": "irrigation",
    "lower_ec_nutrient_adjustment": "nutrient_ec_check",
    "raise_ec_check_supplied_ec": "nutrient_ec_check",
    "ventilation": "ventilation_dehumidification",
    "no_ventilation": "ventilation_dehumidification",
    "shading": "shading_high_temperature",
    "no_shading": "shading_high_temperature",
    "heat_preservation_heating_review": "heating_low_temperature",
    "no_heat_preservation": "heating_low_temperature",
}
NO_CONTROL_NOTICE: Final = "모든 출력은 의사결정 보조이며 실행 전 사람의 확인이 필요합니다."
TEXT_KO: Final = {
    "root-zone moisture may improve": "근권 수분이 개선될 가능성이 있습니다.",
    "EC/salinity stress may dilute if drainage is adequate": "배액이 충분하면 EC/염류 스트레스가 완화될 수 있습니다.",
    "avoids over-wet substrate risk": "배지 과습 위험을 피할 수 있습니다.",
    "water stress may persist under high VPD or radiation": "VPD 또는 일사가 높으면 수분 스트레스가 지속될 수 있습니다.",
    "monitor substrate moisture trend": "배지 수분 추세를 계속 확인해야 합니다.",
    "over-wet substrate can raise disease-environment risk": "배지가 과습해지면 병해 환경 위험이 높아질 수 있습니다.",
    "confirm recent irrigation and drainage before action": "최근 관수와 배액 상태를 확인한 뒤 검토해야 합니다.",
    "salinity stress may decrease after nutrient adjustment review": "양액 조정 검토 후 염류 스트레스가 낮아질 수 있습니다.",
    "supplied EC issue becomes better characterized": "공급 EC 문제를 더 명확히 확인할 수 있습니다.",
    "over-dilution can reduce nutrient availability": "과도한 희석은 양분 이용성을 낮출 수 있습니다.",
    "verify feed EC, drain EC, and drainage ratio first": "공급 EC, 배액 EC, 배액률을 먼저 확인해야 합니다.",
    "raising EC can increase salinity stress if drain EC is already high": "배액 EC가 이미 높다면 EC 상향은 염류 스트레스를 키울 수 있습니다.",
    "treat as EC check, not automatic fertilizer increase": "자동 비료 증량이 아니라 EC 확인 항목으로 다뤄야 합니다.",
    "humidity and disease-environment risk proxy may decrease": "습도와 병해 환경 위험 proxy가 낮아질 수 있습니다.",
    "avoids cold-air ventilation side effects": "찬 공기 유입에 따른 환기 부작용을 피할 수 있습니다.",
    "temperature may drop if outside air is cold": "외기가 차가우면 내부 온도가 떨어질 수 있습니다.",
    "human review required before control changes": "환경 변경 전 사람의 검토가 필요합니다.",
    "humidity and wet-canopy pressure may persist": "습도와 젖은 엽면 압력이 지속될 수 있습니다.",
    "do not ignore sustained high humidity": "고습이 지속되면 방치하지 말고 확인해야 합니다.",
    "heat and radiation stress may decrease": "고온 및 일사 스트레스가 낮아질 수 있습니다.",
    "water demand may decrease": "수분 요구량이 낮아질 수 있습니다.",
    "keeps full light for photosynthesis": "광합성을 위한 빛을 유지할 수 있습니다.",
    "excess shading can reduce photosynthesis": "과도한 차광은 광합성을 낮출 수 있습니다.",
    "compare with radiation forecast and growth stage": "일사 예보와 생육단계를 함께 비교해야 합니다.",
    "heat/radiation stress may persist": "고온/일사 스트레스가 지속될 수 있습니다.",
    "monitor VPD and fruit temperature proxy": "VPD와 과실 온도 proxy를 확인해야 합니다.",
    "low-temperature risk may decrease": "저온 위험이 낮아질 수 있습니다.",
    "avoids heating energy cost": "난방 에너지 비용을 피할 수 있습니다.",
    "energy cost increases": "에너지 비용이 증가합니다.",
    "humidity may rise when ventilation is reduced": "환기를 줄이면 습도가 상승할 수 있습니다.",
    "review energy and humidity tradeoff before heating": "난방 전 에너지와 습도 tradeoff를 검토해야 합니다.",
    "low-temperature stress may persist": "저온 스트레스가 지속될 수 있습니다.",
    "monitor nighttime temperature forecast": "야간 온도 예보를 확인해야 합니다.",
}


@dataclass(frozen=True, slots=True)
class RecommendationReport:
    level1_recommendations: tuple[CoreRecommendation, ...]
    auxiliary_alerts: tuple[CoreRecommendation, ...] = ()
    title: str = "오늘의 온실 관리 추천"
    mode: str = "decision_support"
    requires_human_review: bool = True

    def to_json(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "mode": self.mode,
            "requires_human_review": self.requires_human_review,
            "level1_recommendations": [_recommendation_to_json(item) for item in self.level1_recommendations],
            "auxiliary_alerts": [_recommendation_to_json(item) for item in self.auxiliary_alerts],
        }

    def to_korean_text(self) -> str:
        lines = [self.title, "", NO_CONTROL_NOTICE]
        for index, item in enumerate(self.level1_recommendations, start=1):
            label = ACTION_LABELS_KO.get(item.action, item.action)
            heading = f"{index}순위: {label}" if item.status != "hold" else f"{label} 보류"
            lines.extend(
                [
                    "",
                    heading,
                    f"필요도 점수: {round(item.score)}점",
                    f"상태: {_status_label(item.status)}",
                    "이유:",
                ]
            )
            lines.extend(f"- {reason}" for reason in item.reasons)
            if item.expected_effects:
                lines.append("기대 효과:")
                lines.extend(f"- {_ko_text(effect)}" for effect in item.expected_effects)
            if item.risks:
                lines.append("주의:")
                lines.extend(f"- {_ko_text(risk)}" for risk in item.risks)
            if item.prediction_refs:
                lines.append("예측 참고:")
                lines.extend(f"- {ref}" for ref in item.prediction_refs)
            if item.simulation_refs:
                lines.append("시나리오 참고:")
                lines.extend(f"- {ref}" for ref in item.simulation_refs)
        if self.auxiliary_alerts:
            lines.extend(["", "보조 알림"])
            for item in self.auxiliary_alerts:
                label = ACTION_LABELS_KO.get(item.action, item.action)
                lines.append(f"- {label}: {round(item.score)}점 ({_status_label(item.status)})")
                for reason in item.reasons:
                    lines.append(f"  - {reason}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class RecommendationGenerator:
    def generate(
        self,
        *,
        work_need_scores: tuple[WorkNeedScore, ...],
        predictions: tuple[PredictionResult, ...] = (),
        scenario_results: tuple[ShortHorizonScenarioResult, ...] = (),
        auxiliary_alerts: tuple[WorkNeedScore, ...] = (),
        evidence_rules: tuple[EvidenceRule, ...] = (),
    ) -> RecommendationReport:
        rules_by_action = evidence_rules_by_action_type(evidence_rules)
        level1 = tuple(
            _recommendation_from_score(score, predictions, scenario_results, rules_by_action.get(score.action_type, ()))
            for score in sorted(work_need_scores, key=lambda item: item.score, reverse=True)
        )
        alerts = tuple(
            _recommendation_from_score(score, predictions, (), rules_by_action.get(score.action_type, ()))
            for score in sorted(auxiliary_alerts, key=lambda item: item.score, reverse=True)
        )
        return RecommendationReport(level1_recommendations=level1, auxiliary_alerts=alerts)


def _recommendation_from_score(
    score: WorkNeedScore,
    predictions: tuple[PredictionResult, ...],
    scenario_results: tuple[ShortHorizonScenarioResult, ...],
    evidence_rules: tuple[EvidenceRule, ...] = (),
) -> CoreRecommendation:
    scenario_matches = _scenario_matches(score.action_type, scenario_results)
    return CoreRecommendation(
        action=score.action_type,
        score=score.score,
        priority=_priority(score.score),
        status=score.status,
        reasons=_reasons(score, predictions),
        expected_effects=_expected_effects(score, scenario_matches),
        risks=_risks(score, scenario_matches),
        evidence_rule_ids=_evidence_rule_ids(score, scenario_matches, evidence_rules),
        prediction_refs=_prediction_refs(score.action_type, predictions),
        simulation_refs=_simulation_refs(scenario_matches),
        requires_human_review=True,
        mode="decision_support",
    )


def _reasons(score: WorkNeedScore, predictions: tuple[PredictionResult, ...]) -> tuple[str, ...]:
    reasons: list[str] = []
    if score.status == "hold":
        reasons.append(_hold_reason(score))
    elif score.status == "monitor":
        reasons.append("현재 신호가 강하지 않아 모니터링을 유지합니다.")
    else:
        reasons.extend(_component_reasons(score))
    if not reasons:
        reasons.append("현재 상태와 규칙 기반 점수에서 큰 위험 신호가 제한적입니다.")
    fallback_refs = [item for item in predictions if item.fallback_used]
    if fallback_refs:
        reasons.append("일부 예측은 baseline/fallback 결과이므로 보수적으로 해석해야 합니다.")
    return tuple(reasons)


def _component_reasons(score: WorkNeedScore) -> list[str]:
    reasons: list[str] = []
    if score.moisture_stress > 0:
        reasons.append("배지/근권 수분 스트레스 신호가 있습니다.")
    if score.salinity_stress > 0:
        reasons.append("EC 또는 염류 스트레스 확인이 필요합니다.")
    if score.high_temp_stress > 0:
        reasons.append("고온, 일사, VPD 기반 열 스트레스 가능성이 있습니다.")
    if score.low_temp_stress > 0:
        reasons.append("저온 스트레스 가능성이 있습니다.")
    if score.disease_environment_risk > 0:
        reasons.append("고습 또는 낮은 VPD로 병해 환경 위험 proxy가 증가할 수 있습니다.")
    if score.energy_cost > 0:
        reasons.append("에너지 비용과 습도 상승 가능성을 함께 검토해야 합니다.")
    return reasons


def _hold_reason(score: WorkNeedScore) -> str:
    label = ACTION_LABELS_KO.get(score.action_type, score.action_type)
    return f"{label} 보류: 현재 필요도 점수가 낮아 즉시 실행보다 상태 확인이 적절합니다."


def _expected_effects(
    score: WorkNeedScore,
    scenarios: tuple[ShortHorizonScenarioResult, ...],
) -> tuple[str, ...]:
    effects = [effect for scenario in scenarios for effect in scenario.expected_benefits]
    if effects:
        return tuple(dict.fromkeys(effects))
    if score.status == "recommend":
        return ("관련 스트레스 또는 위험 신호를 낮출 가능성이 있습니다.",)
    return ()


def _risks(
    score: WorkNeedScore,
    scenarios: tuple[ShortHorizonScenarioResult, ...],
) -> tuple[str, ...]:
    risks = [risk for scenario in scenarios for risk in (*scenario.risks, *scenario.warnings)]
    if score.status in {"recommend", "caution"}:
        risks.append("사람의 확인 없이 실행하지 마십시오.")
    return tuple(dict.fromkeys(risks))


def _evidence_rule_ids(
    score: WorkNeedScore,
    scenarios: tuple[ShortHorizonScenarioResult, ...],
    evidence_rules: tuple[EvidenceRule, ...] = (),
) -> tuple[str, ...]:
    ids = [rule_id for scenario in scenarios for rule_id in scenario.evidence_rule_ids]
    ids.extend(rule.rule_id for rule in evidence_rules)
    if not ids:
        ids.append(f"{score.action_type}.score.prototype")
    return tuple(dict.fromkeys(ids))


def _prediction_refs(action_type: str, predictions: tuple[PredictionResult, ...]) -> tuple[str, ...]:
    refs = []
    related_predictions = tuple(
        prediction for prediction in predictions if prediction_relates_to_action(action_type, prediction)
    )
    for prediction in related_predictions:
        label = (
            f"{prediction.target}/{prediction.horizon_hours}h "
            f"value={prediction.predicted_value} delta={prediction.predicted_delta} "
            f"confidence={prediction.confidence:.2f}"
        )
        if prediction.fallback_used:
            label += f" baseline/fallback: {prediction.fallback_reason or prediction.model_used}"
        refs.append(label)
    if not refs:
        refs.append(f"{action_type}: prediction unavailable; baseline/fallback rules used")
    return tuple(refs)


def _scenario_matches(
    action_type: str,
    scenario_results: tuple[ShortHorizonScenarioResult, ...],
) -> tuple[ShortHorizonScenarioResult, ...]:
    return tuple(
        item for item in scenario_results
        if SCENARIO_ACTION_TO_LEVEL1.get(item.action_type) == action_type
    )


def _simulation_refs(scenarios: tuple[ShortHorizonScenarioResult, ...]) -> tuple[str, ...]:
    return tuple(
        f"{item.action_type}: moisture {item.moisture_delta:+.1f}, EC {item.ec_delta:+.2f}, "
        f"humidity {item.humidity_delta:+.1f}, VPD {item.vpd_delta:+.2f}, "
        f"temperature {item.temperature_delta:+.1f}, energy {item.energy_cost_delta:+.1f}"
        for item in scenarios
    )


def _recommendation_to_json(item: CoreRecommendation) -> dict[str, Any]:
    return {
        "action": item.action,
        "action_name": ACTION_LABELS_KO.get(item.action, item.action),
        "score": item.score,
        "priority": item.priority,
        "status": item.status,
        "reasons": list(item.reasons),
        "expected_effects": list(item.expected_effects),
        "risks": list(item.risks),
        "evidence_rule_ids": list(item.evidence_rule_ids),
        "prediction_refs": list(item.prediction_refs),
        "simulation_refs": list(item.simulation_refs),
        "requires_human_review": item.requires_human_review,
        "mode": item.mode,
    }


def _ko_text(text: str) -> str:
    return TEXT_KO.get(text, text)


def _priority(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 55:
        return "medium"
    return "low"


def _status_label(status: str) -> str:
    return {
        "recommend": "추천",
        "caution": "주의",
        "hold": "보류",
        "monitor": "모니터링",
    }.get(status, status)
