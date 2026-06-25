from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias, assert_never

from libsbapi.action_recommenders import (
    disease_environment_risk_proxy,
    harvest_monitoring,
    heating_low_temperature,
    irrigation,
    leaf_removal_caution,
    nutrient_ec_check,
    ph_check,
    shading_high_temperature,
    ventilation_dehumidification,
)
from libsbapi.action_recommenders.common import RecommendationContext
from libsbapi.decision_contract import (
    GreenhouseSnapshot,
    PredictionResult,
    RecommendationResult,
)
from libsbapi.evidence_rules import EvidenceRule, evidence_rules_by_action_type
from libsbapi.prediction_confidence import (
    apply_prediction_gate_to_recommendation,
    gate_prediction_result,
)
from libsbapi.prediction_targets import prediction_relates_to_action


ACTION_MODULES = (
    irrigation,
    nutrient_ec_check,
    ventilation_dehumidification,
    shading_high_temperature,
    heating_low_temperature,
)
SUPPORTING_MODULES = (
    ph_check,
)
AUXILIARY_ALERT_MODULES = (
    disease_environment_risk_proxy,
    harvest_monitoring,
    leaf_removal_caution,
)
MIN_AUXILIARY_PRIORITY = {"medium", "high"}
PRIORITY_RANK = {"low": 1, "medium": 2, "high": 3}
PredictionInput: TypeAlias = PredictionResult | tuple[PredictionResult, ...] | None


@dataclass(frozen=True, slots=True)
class ActionRecommendationEngine:
    evidence_rules: tuple[EvidenceRule, ...]

    def recommend(
        self,
        snapshot: GreenhouseSnapshot,
        prediction: PredictionInput = None,
    ) -> tuple[RecommendationResult, ...]:
        return self._recommend_from_modules(snapshot, prediction, ACTION_MODULES)

    def auxiliary_alerts(
        self,
        snapshot: GreenhouseSnapshot,
        prediction: PredictionInput = None,
    ) -> tuple[RecommendationResult, ...]:
        alerts = self._recommend_from_modules(snapshot, prediction, AUXILIARY_ALERT_MODULES)
        return tuple(item for item in alerts if item.priority in MIN_AUXILIARY_PRIORITY)

    def supporting_recommendations(
        self,
        snapshot: GreenhouseSnapshot,
        prediction: PredictionInput = None,
    ) -> tuple[RecommendationResult, ...]:
        return self._recommend_from_modules(snapshot, prediction, SUPPORTING_MODULES)

    def _recommend_from_modules(
        self,
        snapshot: GreenhouseSnapshot,
        prediction: PredictionInput,
        modules: tuple,
    ) -> tuple[RecommendationResult, ...]:
        grouped_rules = evidence_rules_by_action_type(self.evidence_rules)
        predictions = _normalize_predictions(prediction)
        recommendations: list[RecommendationResult] = []
        for module in modules:
            module_prediction = _prediction_for_action(module.ACTION_TYPE, predictions)
            context = RecommendationContext(
                snapshot=snapshot,
                recent_work_history=snapshot.recent_work_history,
                evidence_rules=grouped_rules.get(module.ACTION_TYPE, ()),
                prediction=module_prediction,
            )
            recommendations.extend(module.recommend(context))
        recommendations = [_gate_if_prediction_exists(item) for item in recommendations]
        return tuple(
            sorted(
                recommendations,
                key=lambda item: (PRIORITY_RANK[item.priority], item.confidence),
                reverse=True,
            )
        )


def _prediction_for_action(
    action_type: str,
    predictions: tuple[PredictionResult, ...],
) -> PredictionResult | None:
    related = tuple(
        prediction for prediction in predictions if prediction_relates_to_action(action_type, prediction)
    )
    if not related:
        return None
    usable = tuple(prediction for prediction in related if gate_prediction_result(prediction).use_model)
    if usable:
        return max(usable, key=lambda item: gate_prediction_result(item).confidence)
    return related[0]


def _gate_if_prediction_exists(item: RecommendationResult) -> RecommendationResult:
    if item.prediction is None:
        return item
    return apply_prediction_gate_to_recommendation(item, gate_prediction_result(item.prediction))


def _normalize_predictions(prediction: PredictionInput) -> tuple[PredictionResult, ...]:
    match prediction:
        case None:
            return ()
        case PredictionResult():
            return (prediction,)
        case tuple():
            return prediction
        case unreachable:
            assert_never(unreachable)
