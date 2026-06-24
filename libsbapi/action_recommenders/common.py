from __future__ import annotations

from dataclasses import dataclass

from libsbapi.decision_contract import (
    EvidenceReference,
    GreenhouseSnapshot,
    PredictionResult,
    RecommendationResult,
    WorkHistoryEvent,
)
from libsbapi.evidence_rules import EvidenceRule
from libsbapi.prediction_confidence import gate_prediction_result


@dataclass(frozen=True, slots=True)
class RecommendationContext:
    snapshot: GreenhouseSnapshot
    recent_work_history: tuple[WorkHistoryEvent, ...]
    evidence_rules: tuple[EvidenceRule, ...]
    prediction: PredictionResult | None = None


@dataclass(frozen=True, slots=True)
class RecommendationDraft:
    action_type: str
    score: float
    reason: str
    expected_effect: str
    risks: tuple[str, ...]
    evidence_rules: tuple[EvidenceRule, ...]
    safety_flags: tuple[str, ...] = ("decision_support_only", "requires_human_review")
    prediction: PredictionResult | None = None


def build_recommendation(draft: RecommendationDraft) -> RecommendationResult:
    confidence = min(max(draft.score, 0.2), 0.82)
    if draft.prediction is not None:
        confidence = min(confidence, draft.prediction.confidence)
    return RecommendationResult(
        action_type=draft.action_type,
        priority=priority_from_score(draft.score),
        confidence=round(confidence, 3),
        reason=draft.reason,
        expected_effect=draft.expected_effect,
        risks=draft.risks,
        evidence_references=evidence_references(draft.evidence_rules),
        safety_flags=draft.safety_flags,
        model_used="literature_manual_rules",
        fallback_used=True,
        prediction=draft.prediction,
    )


def priority_from_score(score: float) -> str:
    if score >= 0.72:
        return "high"
    if score >= 0.42:
        return "medium"
    return "low"


def evidence_references(rules: tuple[EvidenceRule, ...]) -> tuple[EvidenceReference, ...]:
    return tuple(
        EvidenceReference(
            source_type=rule.evidence_level,
            title=rule.source_title,
            reference_id=rule.id,
            note=rule.source_note,
            confidence=0.65,
        )
        for rule in rules
    )


def has_recent_work(context: RecommendationContext, action_type: str) -> bool:
    return any(event.action_type == action_type for event in context.recent_work_history)


def first_available(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return value
    return None


def usable_prediction(context: RecommendationContext) -> PredictionResult | None:
    if context.prediction is None:
        return None
    if gate_prediction_result(context.prediction).use_model:
        return context.prediction
    return None
