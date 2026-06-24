from dataclasses import dataclass, field
from enum import StrEnum, unique
from typing import Final

from .berrynext import BerryNextDecisionEngine, GreenhouseSnapshot, Recommendation


@unique
class CropGrowthStage(StrEnum):
    TRANSPLANTING = "transplanting"
    VEGETATIVE = "vegetative"
    FLOWERING = "flowering"
    FRUITING = "fruiting"
    HARVEST = "harvest"
    RESTING = "resting"


@unique
class FarmWorkType(StrEnum):
    IRRIGATION = "irrigation"
    DISEASE_CONTROL = "disease_control"
    HARVEST = "harvest"
    LEAF_PRUNING = "leaf_pruning"


@unique
class WorkTiming(StrEnum):
    TODAY_MORNING = "today_morning"
    TODAY = "today"
    WITHIN_48H = "within_48h"
    MONITOR = "monitor"


@dataclass(frozen=True, slots=True)
class FarmWorkHistory:
    days_since_irrigation: int | None = None
    days_since_scouting: int | None = None
    days_since_disease_control: int | None = None
    days_since_harvest: int | None = None
    days_since_leaf_pruning: int | None = None


@dataclass(frozen=True, slots=True)
class FarmWorkContext:
    growth_stage: CropGrowthStage
    snapshot: GreenhouseSnapshot
    history: FarmWorkHistory = field(default_factory=FarmWorkHistory)


@dataclass(frozen=True, slots=True)
class FarmWorkTask:
    work_type: FarmWorkType
    timing: WorkTiming
    priority: str
    score: float
    title: str
    reason: str
    safeguards: tuple[str, ...] = ()
    metrics: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True, slots=True)
class DailyFarmWorkPlan:
    summary: str
    tasks: list[FarmWorkTask]
    data_sources: tuple[str, ...]


HARVEST_STAGES: Final = frozenset({CropGrowthStage.FRUITING, CropGrowthStage.HARVEST})
LEAF_PRUNING_STAGES: Final = frozenset(
    {CropGrowthStage.VEGETATIVE, CropGrowthStage.FLOWERING, CropGrowthStage.FRUITING}
)
WORK_SOURCE_LABELS: Final = ("생육단계", "온실환경", "이미지/예찰", "작업이력")
TASK_TIE_BREAK: Final = {
    FarmWorkType.HARVEST: 4,
    FarmWorkType.DISEASE_CONTROL: 3,
    FarmWorkType.IRRIGATION: 2,
    FarmWorkType.LEAF_PRUNING: 1,
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _priority(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _timing(score: float) -> WorkTiming:
    if score >= 0.75:
        return WorkTiming.TODAY_MORNING
    if score >= 0.55:
        return WorkTiming.TODAY
    if score >= 0.35:
        return WorkTiming.WITHIN_48H
    return WorkTiming.MONITOR


def _days_bonus(days: int | None, trigger_days: int, bonus: float) -> float:
    if days is not None and days >= trigger_days:
        return bonus
    return 0.0


def _task_from_recommendation(
    work_type: FarmWorkType,
    title: str,
    recommendation: Recommendation,
) -> FarmWorkTask:
    return FarmWorkTask(
        work_type=work_type,
        timing=_timing(recommendation.score),
        priority=recommendation.priority,
        score=recommendation.score,
        title=title,
        reason=recommendation.reason,
        safeguards=tuple(recommendation.safeguards),
        metrics=tuple(recommendation.metrics.items()),
    )


class DailyFarmWorkDecisionEngine:
    def __init__(self) -> None:
        self.berrynext = BerryNextDecisionEngine()

    def plan_today(self, context: FarmWorkContext) -> DailyFarmWorkPlan:
        irrigation = self.berrynext.irrigation.recommend(context.snapshot)
        disease = self._disease_recommendation(context)
        harvest = self._harvest_recommendation(context)
        leaf_pruning = self._leaf_pruning_recommendation(context)

        tasks = [
            _task_from_recommendation(
                FarmWorkType.IRRIGATION,
                "관수/양액 점검",
                irrigation,
            ),
            _task_from_recommendation(
                FarmWorkType.DISEASE_CONTROL,
                "예찰 후 방제 준비",
                disease,
            ),
            _task_from_recommendation(
                FarmWorkType.HARVEST,
                "수확 우선순위 확인",
                harvest,
            ),
        ]
        if leaf_pruning.score >= 0.35:
            tasks.append(
                _task_from_recommendation(
                    FarmWorkType.LEAF_PRUNING,
                    "적엽 작업 검토",
                    leaf_pruning,
                )
            )

        visible_tasks = [task for task in tasks if task.score >= 0.35]
        ranked = sorted(
            visible_tasks,
            key=lambda task: (task.score, TASK_TIE_BREAK[task.work_type]),
            reverse=True,
        )
        return DailyFarmWorkPlan(
            summary=self._summary(ranked),
            tasks=ranked,
            data_sources=WORK_SOURCE_LABELS,
        )

    def _disease_recommendation(self, context: FarmWorkContext) -> Recommendation:
        base = self.berrynext.disease.recommend(context.snapshot)
        score = base.score
        reasons = [base.reason]
        safeguards = list(base.safeguards)

        if context.history.days_since_scouting is not None and context.history.days_since_scouting >= 3:
            score += 0.12
            reasons.append("recent scouting gap is growing")

        if (
            context.history.days_since_disease_control is not None
            and context.history.days_since_disease_control >= 10
            and base.score >= 0.45
        ):
            score += 0.12
            reasons.append("disease-control interval is long")
            safeguards.append("confirm symptoms before chemical control")

        score = _clamp(score)
        return Recommendation(
            action="scout_and_prepare_disease_control",
            priority=_priority(score),
            score=round(score, 3),
            reason=", ".join(reasons),
            safeguards=safeguards,
            metrics=base.metrics,
        )

    def _harvest_recommendation(self, context: FarmWorkContext) -> Recommendation:
        base = self.berrynext.harvest.recommend(context.snapshot)
        score = base.score
        reasons = [base.reason]

        if context.growth_stage in HARVEST_STAGES:
            score += 0.2
            reasons.append("growth stage is in fruiting or harvest window")

        if context.history.days_since_harvest is not None and context.history.days_since_harvest >= 2:
            score += 0.08
            reasons.append("harvest interval is due")

        score = _clamp(score)
        return Recommendation(
            action="plan_harvest_today",
            priority=_priority(score),
            score=round(score, 3),
            reason=", ".join(reasons),
        )

    def _leaf_pruning_recommendation(self, context: FarmWorkContext) -> Recommendation:
        score = 0.0
        reasons: list[str] = []
        safeguards: list[str] = []
        image = context.snapshot.image

        if context.growth_stage in LEAF_PRUNING_STAGES:
            score += 0.15
            reasons.append("growth stage can benefit from canopy management")

        if image.leaf_density is not None and image.leaf_density >= 0.8:
            score += 0.35
            reasons.append("image signal shows dense canopy")

        if context.snapshot.inside_humidity_pct is not None and context.snapshot.inside_humidity_pct >= 85:
            score += 0.15
            reasons.append("high humidity raises canopy disease pressure")

        score += _days_bonus(context.history.days_since_leaf_pruning, 7, 0.2)
        if context.history.days_since_leaf_pruning is not None and context.history.days_since_leaf_pruning < 5:
            score -= 0.35
            safeguards.append("avoid repeated defoliation too soon")

        score = _clamp(score)
        return Recommendation(
            action="review_leaf_pruning",
            priority=_priority(score),
            score=round(score, 3),
            reason=", ".join(reasons) or "canopy management signal is not strong",
            safeguards=safeguards,
        )

    @staticmethod
    def _summary(tasks: list[FarmWorkTask]) -> str:
        if not tasks:
            return "오늘은 강한 작업 신호가 없어 모니터링 중심으로 운영합니다."
        top_titles = ", ".join(task.title for task in tasks[:3])
        return f"오늘 우선 작업은 {top_titles}입니다."
