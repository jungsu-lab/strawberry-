# /// script
# dependencies = [
#   "streamlit>=1.36.0",
# ]
# ///
# How to run:
#   streamlit run dashboard/greenhouse_dashboard.py

import sys
from pathlib import Path
from typing import Final, TypedDict

try:
    import streamlit as st
except ModuleNotFoundError:
    st = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from libsbapi.decision_contract import CoreRecommendation, CurrentGreenhouseState, PredictionResult, WorkNeedScore
from libsbapi.display_labels import (
    ACTION_LABELS_KO as LEVEL1_ACTION_LABELS_KO,
    AUXILIARY_ALERT_LABELS_KO as LEVEL2_ALERT_LABELS_KO,
    AUXILIARY_RESEARCH_WARNING,
    DASHBOARD_SAFETY_BADGE,
    DASHBOARD_SAFETY_TEXT,
    SCENARIO_LABELS_KO,
    SCORE_COMPONENT_LABELS_KO,
    SECTION_TITLES_KO,
    VARIABLE_LABELS_KO as PREDICTION_TARGET_LABELS_KO,
    scenario_label,
    status_label,
)
from libsbapi.greenhouse_models import (
    DiseaseControlWork,
    DistributionType,
    GreenhouseEnvironment,
    GreenhouseState,
    HarvestWork,
    IrrigationWork,
    LeafPruningWork,
)
from libsbapi.offline_demo import build_demo_from_current_state
from libsbapi.scenario_comparison import ShortHorizonScenarioComparison, ShortHorizonScenarioResult
from libsbapi.simulation_runner import (
    EvidenceLogEntry,
    Scenario,
    ScheduledWork,
    SimulationRecord,
    compare_scenarios,
)


class RecommendationSummaryRow(TypedDict):
    순위: int
    작업: str
    필요도_점수: str
    상태: str
    이유: str
    주의: str


class CurrentStateRow(TypedDict):
    항목: str
    값: str
    단위: str


class PredictionDisplayRow(TypedDict):
    변수: str
    target_id: str
    horizon_hours: int
    현재값: str
    예측_변화량: str
    예측값: str
    신뢰도: str
    model_used: str
    fallback_used: bool
    fallback_reason: str


class ScenarioDisplayRow(TypedDict):
    후보: str
    내부_action_id: str
    수분_영향: str
    EC_염류_영향: str
    습도_VPD_영향: str
    온도_영향: str
    병해환경_프록시: str
    에너지비용_프록시: str
    기대효과: str
    위험_주의: str
    신뢰도: str
    최종추천_반영: str


class WorkScoreDisplayRow(TypedDict):
    순위: int
    작업: str
    필요도_점수: str
    상태: str
    신뢰도: str
    주요_위험요인: str
    사람_검토_필요: str
    action_id: str


class AuxiliaryAlertDisplayRow(TypedDict):
    구분: str
    알림: str
    표시_상태: str
    점수: str
    설명: str
    사람_검토_필요: str


class TimelineRow(TypedDict):
    scenario: str
    day: int
    metric: str
    value: float


class SummaryRow(TypedDict):
    scenario: str
    moisture: float
    drain_ec: float
    disease_risk: float
    ripe_ratio: float
    fruit_count: int
    leaf_density: float
    ventilation: float
    yield_kg: float
    quality_risk: float
    confidence: float


class EvidenceRow(TypedDict):
    scenario: str
    day: int
    action: str
    kind: str
    message: str


METRIC_LABELS: Final[dict[str, str]] = {
    "substrate_moisture_pct": "배지수분",
    "drain_ec": "배액 EC",
    "disease_risk": "병해 환경 위험 프록시",
    "ripe_fruit_ratio": "수확 가능성",
    "leaf_density": "엽밀도",
    "ventilation_score": "환기 점수",
    "marketable_yield_kg": "상품 수확량 프록시",
    "quality_risk": "품질 위험 프록시",
}
DEFAULT_METRICS: Final[tuple[str, ...]] = (
    "substrate_moisture_pct",
    "disease_risk",
    "marketable_yield_kg",
    "quality_risk",
)
DEFAULT_SCENARIOS: Final[tuple[str, ...]] = ("무작업", "관수 중심", "예찰+적엽 검토", "수확 가능성 점검")
SCENARIO_TO_LEVEL1: Final[dict[str, str]] = {
    "irrigation": "irrigation",
    "lower_ec_nutrient_adjustment": "nutrient_ec_check",
    "ventilation": "ventilation_dehumidification",
    "shading": "shading_high_temperature",
    "heat_preservation_heating_review": "heating_low_temperature",
}
GROWTH_STAGE_OPTIONS: Final[dict[str, str]] = {
    "vegetative": "영양생장기",
    "flowering": "개화기",
    "fruiting": "착과기",
    "harvest": "수확기",
}
TIME_OF_DAY_OPTIONS: Final[dict[str, str]] = {
    "morning": "오전",
    "afternoon": "오후",
    "evening": "저녁",
    "night": "야간",
}
DAY_NIGHT_OPTIONS: Final[dict[str, str]] = {
    "day": "낮",
    "night": "밤",
}


def main() -> None:
    if st is None:
        print("Streamlit is optional for the offline dashboard.")
        print("Install with: pip install streamlit")
        print("CLI demo works without Streamlit: python3 -m examples.berrynext_today_recommendation")
        return
    _ = st.set_page_config(page_title="BerryNext 온실 의사결정 보조", layout="wide")
    _ = st.title("BerryNext 온실 의사결정 보조 대시보드")
    _ = st.caption(
        "현재 온실 상태와 1~3시간 환경 변화 예측, 작업 시나리오 비교, 문헌/매뉴얼 기준 룰을 결합해 "
        "오늘 필요한 온실 관리 작업을 추천합니다."
    )
    _ = st.markdown(f"`{DASHBOARD_SAFETY_BADGE}`")

    demo_tab, legacy_tab = st.tabs(("오늘 추천 파이프라인", "보조 알림 시뮬레이션"))
    with demo_tab:
        _render_decision_support_demo()
    with legacy_tab:
        _render_legacy_simulator()


def _render_decision_support_demo() -> None:
    input_state, context_payload = _decision_support_state_controls()
    demo = build_demo_from_current_state(input_state, context_payload=context_payload)
    state = demo.current_state
    _ = st.subheader(SECTION_TITLES_KO["recommendation_summary"])
    _ = st.caption("오늘 어떤 온실 관리 작업을 우선적으로 해야 하는가?")
    for row in _recommendation_summary_rows(demo.recommendation_report.level1_recommendations):
        with st.container(border=True):
            _ = st.markdown(f"**{row['순위']}순위: {row['작업']} · {row['필요도_점수']} · {row['상태']}**")
            _ = st.write("이유:")
            for reason in row["이유"].split(" | "):
                _ = st.write(f"- {reason}")
            if row["주의"]:
                _ = st.write("주의:")
                for risk in row["주의"].split(" | "):
                    _ = st.write(f"- {risk}")
    for note in _conflict_notes(demo.recommendation_report.level1_recommendations, state):
        _ = st.warning(note)

    _ = st.subheader(SECTION_TITLES_KO["current_state"])
    _ = st.caption("배지수분과 근권수분은 다른 센서/계산값일 수 있으므로 가능한 경우 별도 표시합니다.")
    _ = st.dataframe(
        _current_state_rows(state),
        hide_index=True,
        width="stretch",
    )

    _ = st.subheader(SECTION_TITLES_KO["prediction"])
    _ = st.info("현재 데모는 기준선 예측기를 사용합니다. GAM은 향후 단기 환경 변화량 예측기로 연결될 예정입니다.")
    _ = st.dataframe(
        _prediction_rows(demo.predictions),
        hide_index=True,
        width="stretch",
    )

    _ = st.subheader(SECTION_TITLES_KO["scenario_comparison"])
    _ = st.caption(demo.scenario_report.not_training_label_notice)
    if demo.scenario_input_warnings:
        _ = st.warning("시나리오 입력 대체값: " + " / ".join(demo.scenario_input_warnings))
    _ = st.dataframe(
        _scenario_rows(demo.scenario_report, demo.recommendation_report.level1_recommendations),
        hide_index=True,
        width="stretch",
    )

    _ = st.subheader(SECTION_TITLES_KO["work_need_score"])
    _ = st.dataframe(
        _work_score_rows(demo.work_scores),
        hide_index=True,
        width="stretch",
    )
    with st.expander("내부 action id와 원시 점수 보기"):
        _ = st.dataframe(
            [
                {
                    "action_id": score.action_type,
                    "score": score.score,
                    "status": score.status,
                    "confidence": score.confidence,
                    "components": score.components,
                }
                for score in demo.work_scores
            ],
            hide_index=True,
            width="stretch",
        )

    _ = st.subheader(SECTION_TITLES_KO["auxiliary_alerts"])
    _ = st.caption("Level 2 알림은 핵심 작업 순위가 아니라 예찰·확인용 프록시입니다.")
    if demo.recommendation_report.auxiliary_alerts:
        _ = st.dataframe(
            _auxiliary_alert_rows(demo.recommendation_report.auxiliary_alerts),
            hide_index=True,
            width="stretch",
        )
    else:
        _ = st.write("표시 임계값을 넘은 보조 알림이 없습니다.")

    _ = st.info(DASHBOARD_SAFETY_TEXT)


def _decision_support_state_controls() -> tuple[CurrentGreenhouseState, dict]:
    with st.sidebar.expander("오늘 추천 파이프라인 입력", expanded=True):
        _ = st.markdown("**1. 생육 단계 / 시간 정보**")
        growth_stage = st.selectbox(
            "생육 단계",
            options=tuple(GROWTH_STAGE_OPTIONS),
            index=3,
            format_func=GROWTH_STAGE_OPTIONS.__getitem__,
            key="main_growth_stage",
        )
        time_of_day = st.selectbox(
            "시간대",
            options=tuple(TIME_OF_DAY_OPTIONS),
            index=0,
            format_func=TIME_OF_DAY_OPTIONS.__getitem__,
            key="main_time_of_day",
        )
        day_night = st.radio(
            "낮/밤 여부",
            options=tuple(DAY_NIGHT_OPTIONS),
            index=0,
            format_func=DAY_NIGHT_OPTIONS.__getitem__,
            horizontal=True,
            key="main_day_night",
        )

        _ = st.markdown("**2. Level 1 핵심 온실 상태**")
        air_temp = st.slider("내부 온도 (℃)", 5.0, 40.0, 27.5, 0.5, key="main_air_temp")
        humidity = st.slider("습도 (%)", 30.0, 100.0, 91.0, 1.0, key="main_humidity")
        vpd = st.slider("VPD (kPa)", 0.0, 2.5, 0.33, 0.01, key="main_vpd")
        solar_radiation = st.slider("일사량 (W/m²)", 0.0, 1000.0, 540.0, 10.0, key="main_solar")
        root_zone_moisture = st.slider("배지/근권수분 (%)", 0.0, 100.0, 31.0, 1.0, key="main_root_moisture")
        feed_ec = st.slider("급액 EC", 0.0, 5.0, 1.2, 0.1, key="main_feed_ec")
        drain_ec = st.slider("배액 EC", 0.0, 5.0, 1.3, 0.1, key="main_drain_ec")
        root_ec = st.slider("근권 EC", 0.0, 5.0, 1.4, 0.1, key="main_root_ec")
        ph = st.slider("pH", 4.0, 8.0, 5.8, 0.1, key="main_ph")

        _ = st.markdown("**3. 외부 환경 / 예측 보조**")
        outside_temp = st.slider("외기 온도 (℃)", -10.0, 35.0, 12.0, 0.5, key="main_outside_temp")
        outside_humidity = st.slider("외기 습도 (%)", 0.0, 100.0, 74.0, 1.0, key="main_outside_humidity")
        rain_probability = st.slider("강우 확률 (%)", 0.0, 100.0, 20.0, 1.0, key="main_rain_probability")
        leaf_wetness_hours = st.slider("엽면젖음 시간", 0.0, 24.0, 0.0, 0.5, key="main_leaf_wetness_hours")
        co2 = st.slider("CO₂", 250.0, 1200.0, 430.0, 10.0, key="main_co2")

        with st.expander("4. 선택 입력: Level 2 보조 알림", expanded=False):
            disease_risk = st.slider("병해 예찰 위험", 0.0, 1.0, 0.04, 0.01, key="main_disease_risk")
            harvest_possibility = st.slider("수확 가능성", 0.0, 1.0, 0.86, 0.01, key="main_harvest_possibility")
            coloring_pct = st.slider("착색률", 0.0, 100.0, 82.0, 1.0, key="main_coloring_pct")
            fruit_count = st.slider("과실 수", 0, 200, 52, 1, key="main_fruit_count")
            leaf_density = st.slider("엽밀도", 0.0, 1.0, 0.88, 0.01, key="main_leaf_density")
            old_or_diseased_leaf_level = st.slider("노엽/병든 잎 수준", 0.0, 1.0, 0.45, 0.01, key="main_old_leaf_level")
            quality_risk = st.slider("품질 위험", 0.0, 1.0, 0.14, 0.01, key="main_quality_risk")
    state = _state_from_decision_support_inputs(
        air_temp=air_temp,
        humidity=humidity,
        vpd=vpd,
        solar_radiation=solar_radiation,
        root_zone_moisture=root_zone_moisture,
        drain_ec=drain_ec,
        root_ec=root_ec,
        feed_ec=feed_ec,
        feed_ph=ph,
        drain_ph=ph,
        outside_temp=outside_temp,
        outside_humidity=outside_humidity,
        co2=co2,
        growth_stage=growth_stage,
        time_of_day="night" if day_night == "night" else time_of_day,
    )
    context_payload = _context_payload_from_sidebar(
        rain_probability=rain_probability,
        leaf_wetness_hours=leaf_wetness_hours,
        disease_risk=disease_risk,
        harvest_possibility=harvest_possibility,
        coloring_pct=coloring_pct,
        fruit_count=fruit_count,
        leaf_density=leaf_density,
        old_or_diseased_leaf_level=old_or_diseased_leaf_level,
        quality_risk=quality_risk,
    )
    return state, context_payload


def _state_from_decision_support_inputs(
    *,
    air_temp: float,
    humidity: float,
    vpd: float,
    solar_radiation: float,
    root_zone_moisture: float,
    drain_ec: float,
    root_ec: float | None,
    feed_ec: float | None,
    feed_ph: float | None = None,
    drain_ph: float | None = None,
    outside_temp: float | None = None,
    outside_humidity: float | None = None,
    co2: float | None = None,
    growth_stage: str | None = None,
    time_of_day: str | None = None,
) -> CurrentGreenhouseState:
    warnings = []
    missing_fields = []
    if root_ec is None:
        missing_fields.append("root_ec")
        warnings.append("root_ec missing, EC score confidence reduced")
    if feed_ec is None:
        missing_fields.append("feed_ec")
        warnings.append("feed_ec missing, EC score confidence reduced")
    return CurrentGreenhouseState(
        air_temp=air_temp,
        humidity=humidity,
        vpd=vpd,
        solar_radiation=solar_radiation,
        root_zone_moisture=root_zone_moisture,
        substrate_moisture=root_zone_moisture,
        drain_ec=drain_ec,
        root_ec=root_ec,
        feed_ec=feed_ec,
        feed_ph=feed_ph,
        drain_ph=drain_ph,
        outside_temp=outside_temp,
        outside_humidity=outside_humidity,
        co2=co2,
        growth_stage=_normalize_growth_stage(growth_stage),
        time_of_day=_normalize_time_of_day(time_of_day),
        source_labels=("dashboard_sidebar",),
        missing_fields=tuple(missing_fields),
        quality_warnings=tuple(warnings),
    )


def _context_payload_from_sidebar(
    *,
    rain_probability: float,
    leaf_wetness_hours: float,
    disease_risk: float,
    harvest_possibility: float,
    coloring_pct: float,
    fruit_count: int,
    leaf_density: float,
    old_or_diseased_leaf_level: float,
    quality_risk: float,
) -> dict:
    return {
        "snapshot": {
            "weather": {
                "rain_probability": rain_probability,
                "leaf_wetness_hours": leaf_wetness_hours,
            },
            "image": {
                "disease_spot_ratio": disease_risk,
                "ripe_fruit_ratio": harvest_possibility,
                "coloring_pct": coloring_pct,
                "fruit_count": fruit_count,
                "leaf_density": leaf_density,
                "old_or_diseased_leaf_level": old_or_diseased_leaf_level,
                "quality_risk": quality_risk,
            },
        }
    }


def _normalize_growth_stage(value: str | None) -> str | None:
    if value is None:
        return None
    reverse = {label: key for key, label in GROWTH_STAGE_OPTIONS.items()}
    return reverse.get(value, value)


def _normalize_time_of_day(value: str | None) -> str | None:
    if value is None:
        return None
    reverse = {label: key for key, label in TIME_OF_DAY_OPTIONS.items()}
    return reverse.get(value, value)


def _recommendation_summary_rows(
    recommendations: tuple[CoreRecommendation, ...],
) -> list[RecommendationSummaryRow]:
    rows: list[RecommendationSummaryRow] = []
    level1 = [item for item in recommendations if item.action in LEVEL1_ACTION_LABELS_KO]
    for rank, item in enumerate(sorted(level1, key=lambda rec: rec.score, reverse=True), start=1):
        rows.append(
            RecommendationSummaryRow(
                순위=rank,
                작업=LEVEL1_ACTION_LABELS_KO[item.action],
                필요도_점수=f"{item.score:.0f}점",
                상태=status_label(item.status),
                이유=" | ".join(item.reasons[:3]),
                주의=" | ".join((*item.risks, *_fallback_warnings(item))[:3]),
            )
        )
    return rows


def _current_state_rows(state: CurrentGreenhouseState) -> list[CurrentStateRow]:
    return [
        CurrentStateRow(항목="내부 온도", 값=_value(state.air_temp), 단위="℃"),
        CurrentStateRow(항목="습도", 값=_value(state.humidity), 단위="%"),
        CurrentStateRow(항목="VPD", 값=_value(state.vpd), 단위="kPa"),
        CurrentStateRow(항목="일사량", 값=_value(state.solar_radiation), 단위="W/m²"),
        CurrentStateRow(항목="배지수분", 값=_value(state.substrate_moisture), 단위="%"),
        CurrentStateRow(항목="근권수분", 값=_value(state.root_zone_moisture), 단위="%"),
        CurrentStateRow(항목="급액 EC", 값=_value(state.feed_ec), 단위="dS/m"),
        CurrentStateRow(항목="배액 EC", 값=_value(state.drain_ec), 단위="dS/m"),
        CurrentStateRow(항목="근권 EC", 값=_value(state.root_ec), 단위="dS/m"),
        CurrentStateRow(항목="급액 pH", 값=_value(state.feed_ph), 단위="pH"),
        CurrentStateRow(항목="배액 pH", 값=_value(state.drain_ph), 단위="pH"),
        CurrentStateRow(항목="외기 온도", 값=_value(state.outside_temp), 단위="℃"),
        CurrentStateRow(항목="외기 습도", 값=_value(state.outside_humidity), 단위="%"),
        CurrentStateRow(항목="생육 단계", 값=state.growth_stage or "데이터 없음", 단위="-"),
        CurrentStateRow(항목="시간대", 값=state.time_of_day or "데이터 없음", 단위="-"),
    ]


def _prediction_rows(predictions: tuple[PredictionResult, ...]) -> list[PredictionDisplayRow]:
    return [
        PredictionDisplayRow(
            변수=PREDICTION_TARGET_LABELS_KO.get(prediction.target, prediction.target),
            target_id=prediction.target,
            horizon_hours=prediction.horizon_hours,
            현재값=_value(prediction.current_value),
            예측_변화량=_signed_value(prediction.predicted_delta),
            예측값=_value(prediction.predicted_value),
            신뢰도=f"{prediction.confidence:.2f}",
            model_used=prediction.model_used,
            fallback_used=prediction.fallback_used,
            fallback_reason=prediction.fallback_reason or "",
        ) | {"예측 변화량": _signed_value(prediction.predicted_delta)}
        for prediction in predictions
    ]


def _scenario_rows(
    report: ShortHorizonScenarioComparison,
    recommendations: tuple[CoreRecommendation, ...],
) -> list[ScenarioDisplayRow]:
    recommendation_actions = {
        item.action for item in recommendations if item.action in LEVEL1_ACTION_LABELS_KO and item.status in {"recommend", "caution"}
    }
    rows: list[ScenarioDisplayRow] = []
    for item in report.scenarios:
        if item.action_type not in SCENARIO_LABELS_KO:
            continue
        reflected_action = SCENARIO_TO_LEVEL1.get(item.action_type)
        reflected = reflected_action in recommendation_actions if reflected_action else False
        rows.append(
            ScenarioDisplayRow(
                후보=scenario_label(item.action_type),
                내부_action_id=item.action_type,
                수분_영향=_signed_value(item.moisture_delta),
                EC_염류_영향=f"EC {_signed_value(item.ec_delta)} / 염류 {_signed_value(item.salinity_stress_delta)}",
                습도_VPD_영향=f"습도 {_signed_value(item.humidity_delta)} / VPD {_signed_value(item.vpd_delta)}",
                온도_영향=_signed_value(item.temperature_delta),
                병해환경_프록시=_signed_value(item.disease_environment_risk_delta),
                에너지비용_프록시=_signed_value(item.energy_cost_delta),
                기대효과="; ".join(item.expected_benefits),
                위험_주의="; ".join((*item.risks, *item.warnings)),
                신뢰도=f"{item.confidence:.2f}",
                최종추천_반영="예" if reflected else "아니오",
            )
        )
    return rows


def _work_score_rows(scores: tuple[WorkNeedScore, ...]) -> list[WorkScoreDisplayRow]:
    core_scores = [score for score in scores if score.action_type in LEVEL1_ACTION_LABELS_KO]
    ranked = sorted(core_scores, key=lambda score: score.score, reverse=True)
    return [
        WorkScoreDisplayRow(
            순위=rank,
            작업=LEVEL1_ACTION_LABELS_KO[score.action_type],
            필요도_점수=f"{score.score:.0f}점",
            상태=status_label(score.status),
            신뢰도=f"{score.confidence:.2f}",
            주요_위험요인=_risk_component_text(score),
            사람_검토_필요="예" if score.requires_human_review else "아니오",
            action_id=score.action_type,
        )
        for rank, score in enumerate(ranked, start=1)
    ]


def _auxiliary_alert_rows(alerts: tuple[CoreRecommendation, ...]) -> list[AuxiliaryAlertDisplayRow]:
    return [
        AuxiliaryAlertDisplayRow(
            구분="Level 2 보조 알림",
            알림=LEVEL2_ALERT_LABELS_KO.get(item.action, item.action),
            표시_상태=_auxiliary_status_label(item),
            점수=f"{item.score:.0f}점",
            설명=_auxiliary_description(item),
            사람_검토_필요="예",
        ) | {"표시 상태": _auxiliary_status_label(item)}
        for item in alerts
        if item.action in LEVEL2_ALERT_LABELS_KO
    ]


def _conflict_notes(
    recommendations: tuple[CoreRecommendation, ...],
    state: CurrentGreenhouseState,
) -> list[str]:
    recommended = {item.action for item in recommendations if item.status in {"recommend", "caution"}}
    notes: list[str] = []
    if (
        {"ventilation_dehumidification", "irrigation"} <= recommended
        and state.humidity is not None
        and state.vpd is not None
        and state.humidity >= 85.0
        and state.vpd <= 0.45
    ):
        notes.append(
            "환기와 관수가 함께 높게 나온 상태입니다. 고습·저VPD에서는 관수가 습도 또는 과습 위험을 키울 수 있으므로 "
            "환기와 배지수분·배액 상태 확인을 먼저 고려하십시오."
        )
    if {"heating_low_temperature", "ventilation_dehumidification"} <= recommended:
        notes.append("보온 또는 난방 검토와 환기가 함께 필요하면 에너지 비용과 습도 배출 사이의 균형을 먼저 검토하십시오.")
    if "shading_high_temperature" in recommended:
        notes.append("차광은 광합성에 필요한 일사도 줄일 수 있으므로 부분 차광 또는 시간대별 검토가 필요합니다.")
    return notes


def _risk_component_text(score: WorkNeedScore) -> str:
    labels = {
        "moisture_stress": SCORE_COMPONENT_LABELS_KO["moisture_stress"],
        "salinity_stress": SCORE_COMPONENT_LABELS_KO["salinity_stress"],
        "high_temp_stress": SCORE_COMPONENT_LABELS_KO["high_temp_stress"],
        "low_temp_stress": SCORE_COMPONENT_LABELS_KO["low_temp_stress"],
        "disease_environment_risk": SCORE_COMPONENT_LABELS_KO["disease_environment_risk"],
        "energy_cost": SCORE_COMPONENT_LABELS_KO["energy_cost"],
    }
    active = [labels[name] for name, value in score.components.items() if value > 0]
    return ", ".join(active) if active else "특이 위험 낮음"


def _auxiliary_status_label(item: CoreRecommendation) -> str:
    if item.action == "harvest_monitoring" and item.status == "recommend":
        return "검토 필요"
    if item.status == "recommend":
        return "예찰 권장"
    if item.status == "caution":
        return "주의"
    if item.status == "hold":
        return "검토 필요"
    return "모니터링"


def _auxiliary_description(item: CoreRecommendation) -> str:
    if item.action == "disease_environment_risk_proxy":
        return "병해 환경 위험 프록시입니다. 실제 병해 진단이 아니라 예찰 권장 신호입니다."
    if item.action == "harvest_monitoring":
        return "수확 가능성 알림입니다. 신뢰 판단에는 착색, 과실 수, 이미지 또는 생육 데이터 확인이 필요합니다."
    if item.action == "leaf_removal_caution":
        return "적엽 검토 알림입니다. 캐노피/이미지 근거 없이 강한 적엽 작업을 권하지 않습니다."
    return "보조 확인 신호입니다."


def _fallback_warnings(item: CoreRecommendation) -> tuple[str, ...]:
    if any("fallback" in ref or "baseline" in ref or "기준선" in ref or "대체 예측" in ref for ref in item.prediction_refs):
        return ("일부 예측은 기준선 예측기 결과이므로 실제 작업 전 현장 확인이 필요합니다.",)
    return ()


def _status_label(status: str) -> str:
    return {
        "recommend": "추천",
        "caution": "주의",
        "hold": "보류",
        "monitor": "모니터링",
    }.get(status, status)


def _value(value: float | None) -> str:
    return "데이터 없음" if value is None else f"{value:.2f}"


def _signed_value(value: float | None) -> str:
    return "데이터 없음" if value is None else f"{value:.2f}"


def _render_legacy_simulator() -> None:
    _ = st.warning(AUXILIARY_RESEARCH_WARNING)
    state = _state_controls()
    environment = _environment_controls()
    days = st.sidebar.slider("시뮬레이션 기간", min_value=3, max_value=14, value=7, step=1)
    scenarios = _scenario_controls(state, environment, days)

    comparison = compare_scenarios(scenarios)
    selected_metrics = st.multiselect(
        "비교 지표",
        options=tuple(METRIC_LABELS),
        default=DEFAULT_METRICS,
        format_func=METRIC_LABELS.__getitem__,
    )

    _render_summary(comparison.end_states)
    _render_chart(comparison.timeline, tuple(selected_metrics))
    _render_tables(comparison.end_states, comparison.evidence_log)


def _state_controls() -> GreenhouseState:
    _ = st.sidebar.header("보조 알림 시뮬레이션 상태")
    substrate_moisture = st.sidebar.slider("배지/근권수분 (%)", 30.0, 90.0, 56.0, 1.0)
    drain_ec = st.sidebar.slider("배액 EC", 0.8, 3.5, 1.8, 0.1)
    ventilation_score = st.sidebar.slider("환기 상태 프록시", 0.0, 1.0, 0.36, 0.01)
    with st.sidebar.expander("선택 입력: Level 2 보조 알림 프록시", expanded=False):
        disease_risk = st.slider("병해 예찰 위험", 0.0, 1.0, 0.42, 0.01)
        ripe_fruit_ratio = st.slider("수확 가능성", 0.0, 1.0, 0.62, 0.01)
        fruit_count = st.slider("과실 수", 20, 180, 95, 1)
        leaf_density = st.slider("엽밀도", 0.2, 1.0, 0.78, 0.01)
        yield_potential = st.slider("예상 생산성 보조값", 0.5, 1.3, 1.0, 0.01)
        quality_risk = st.slider("품질 위험", 0.0, 1.0, 0.14, 0.01)
        coloring_pct = st.slider("착색률", 50.0, 100.0, 82.0, 1.0)
        old_or_diseased_leaf_level = st.slider("노엽/병든 잎 수준", 0.0, 1.0, 0.45, 0.01)
    return GreenhouseState(
        substrate_moisture_pct=substrate_moisture,
        drain_ec=drain_ec,
        disease_risk=disease_risk,
        ripe_fruit_ratio=ripe_fruit_ratio,
        fruit_count=fruit_count,
        leaf_density=leaf_density,
        ventilation_score=ventilation_score,
        yield_potential=yield_potential,
        marketable_yield_kg=0.0,
        quality_risk=quality_risk,
        coloring_pct=coloring_pct,
        distribution_type=DistributionType.ROOM_TEMP,
        old_or_diseased_leaf_level=old_or_diseased_leaf_level,
    )


def _environment_controls() -> GreenhouseEnvironment:
    _ = st.sidebar.header("보조 알림 시뮬레이션 외부 조건")
    return GreenhouseEnvironment(
        solar_radiation_w_m2=st.sidebar.slider("일사량 (W/m²)", 100.0, 900.0, 520.0, 10.0),
        vpd_kpa=st.sidebar.slider("VPD (kPa)", 0.1, 2.0, 0.38, 0.01),
        humidity_pct=st.sidebar.slider("습도 (%)", 45.0, 100.0, 89.0, 1.0),
        rain_probability=st.sidebar.slider("강우 확률 (%)", 0.0, 100.0, 55.0, 1.0),
        inside_temperature_c=st.sidebar.slider("내부 온도 (℃)", 12.0, 35.0, 25.0, 0.5),
        leaf_wetness_hours=st.sidebar.slider("엽면젖음 시간", 0.0, 12.0, 5.0, 0.5),
    )


def _scenario_controls(
    state: GreenhouseState,
    environment: GreenhouseEnvironment,
    days: int,
) -> tuple[Scenario, ...]:
    _ = st.sidebar.header("보조 알림 시나리오 조건")
    irrigation_volume = st.sidebar.slider("관수량 (L)", 0.0, 3.0, 1.2, 0.1)
    scouting_effectiveness = st.sidebar.slider("예찰 후 위험 완화 효과", 0.0, 1.0, 0.55, 0.01)
    harvest_review_ratio = st.sidebar.slider("수확 확인 비율", 0.0, 1.0, 0.45, 0.01)
    leaf_review_ratio = st.sidebar.slider("적엽 확인 비율", 0.0, 0.5, 0.18, 0.01)

    scenario_options = {
        "무작업": (),
        "관수 중심": (
            ScheduledWork(day=1, work=IrrigationWork(volume_l=irrigation_volume)),
            ScheduledWork(day=3, work=IrrigationWork(volume_l=irrigation_volume * 0.7)),
        ),
        "예찰+적엽 검토": (
            ScheduledWork(day=1, work=DiseaseControlWork(effectiveness=scouting_effectiveness)),
            ScheduledWork(day=2, work=LeafPruningWork(removal_ratio=leaf_review_ratio)),
        ),
        "수확 가능성 점검": (
            ScheduledWork(day=1, work=HarvestWork(pick_ratio=harvest_review_ratio)),
        ),
        "수확 가능성 지연 점검": (
            ScheduledWork(day=min(3, days), work=HarvestWork(pick_ratio=harvest_review_ratio, delayed_days=2)),
        ),
    }
    selected = st.sidebar.multiselect(
        "비교 시나리오",
        options=tuple(scenario_options),
        default=DEFAULT_SCENARIOS,
    )

    if not selected:
        _ = st.error("비교 시나리오를 하나 이상 선택해야 합니다.")
        st.stop()

    return tuple(
        Scenario(
            name=name,
            initial_state=state,
            environment=environment,
            days=days,
            schedule=scenario_options[name],
        )
        for name in selected
    )


def _render_summary(end_states: tuple[SimulationRecord, ...]) -> None:
    _ = st.subheader(SECTION_TITLES_KO["simulation_final_state"])
    columns = st.columns(min(4, len(end_states)))
    for column, record in zip(columns, end_states, strict=False):
        with column:
            _ = st.metric(record.scenario, f"{record.marketable_yield_kg:.2f} kg")
            summary = (
                f"병해 예찰 {record.disease_risk:.2f} · 품질 {record.quality_risk:.2f} · 수분 "
                f"{record.substrate_moisture_pct:.1f}%"
            )
            _ = st.caption(summary)


def _render_chart(
    timeline: tuple[SimulationRecord, ...],
    selected_metrics: tuple[str, ...],
) -> None:
    _ = st.subheader(SECTION_TITLES_KO["daily_change"])
    if not selected_metrics:
        _ = st.warning("비교 지표를 하나 이상 선택해야 합니다.")
        return

    for metric in selected_metrics:
        rows = _timeline_rows(timeline, (metric,))
        _ = st.markdown(f"#### {METRIC_LABELS[metric]}")
        _ = st.line_chart(
            rows,
            x="day",
            y="value",
            color="scenario",
            height=320,
        )


def _render_tables(
    end_states: tuple[SimulationRecord, ...],
    evidence_log: tuple[EvidenceLogEntry, ...],
) -> None:
    summary_tab, evidence_tab = st.tabs((SECTION_TITLES_KO["summary_table"], "근거 로그"))
    with summary_tab:
        _ = st.dataframe(_summary_rows(end_states), width="stretch", hide_index=True)
    with evidence_tab:
        _ = st.dataframe(_evidence_rows(evidence_log), width="stretch", hide_index=True)


def _timeline_rows(
    timeline: tuple[SimulationRecord, ...],
    selected_metrics: tuple[str, ...],
) -> list[TimelineRow]:
    rows: list[TimelineRow] = []
    for record in timeline:
        values = _metric_values(record)
        for metric in selected_metrics:
            rows.append(
                TimelineRow(
                    scenario=record.scenario,
                    day=record.day,
                    metric=METRIC_LABELS[metric],
                    value=values[metric],
                ),
            )
    return rows


def _metric_values(record: SimulationRecord) -> dict[str, float]:
    return {
        "substrate_moisture_pct": record.substrate_moisture_pct,
        "drain_ec": record.drain_ec,
        "disease_risk": record.disease_risk,
        "ripe_fruit_ratio": record.ripe_fruit_ratio,
        "leaf_density": record.leaf_density,
        "ventilation_score": record.ventilation_score,
        "marketable_yield_kg": record.marketable_yield_kg,
        "quality_risk": record.quality_risk,
    }


def _summary_rows(end_states: tuple[SimulationRecord, ...]) -> list[SummaryRow]:
    return [
        SummaryRow(
            scenario=record.scenario,
            moisture=record.substrate_moisture_pct,
            drain_ec=record.drain_ec,
            disease_risk=record.disease_risk,
            ripe_ratio=record.ripe_fruit_ratio,
            fruit_count=record.fruit_count,
            leaf_density=record.leaf_density,
            ventilation=record.ventilation_score,
            yield_kg=record.marketable_yield_kg,
            quality_risk=record.quality_risk,
            confidence=record.confidence,
        )
        for record in end_states
    ]


def _evidence_rows(evidence_log: tuple[EvidenceLogEntry, ...]) -> list[EvidenceRow]:
    return [
        EvidenceRow(
            scenario=entry.scenario,
            day=entry.day,
            action=entry.action,
            kind=entry.kind,
            message=entry.message,
        )
        for entry in evidence_log
    ]


if __name__ == "__main__":
    main()
