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

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from libsbapi.greenhouse_models import (
    DiseaseControlWork,
    DistributionType,
    GreenhouseEnvironment,
    GreenhouseState,
    HarvestWork,
    IrrigationWork,
    LeafPruningWork,
)
from libsbapi.simulation_runner import (
    EvidenceLogEntry,
    Scenario,
    ScheduledWork,
    SimulationRecord,
    compare_scenarios,
)


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
    "disease_risk": "병해 위험",
    "ripe_fruit_ratio": "익은 과실 비율",
    "leaf_density": "엽밀도",
    "ventilation_score": "환기 점수",
    "marketable_yield_kg": "상품 수확량",
    "quality_risk": "품질 위험",
}
DEFAULT_METRICS: Final[tuple[str, ...]] = (
    "substrate_moisture_pct",
    "disease_risk",
    "marketable_yield_kg",
    "quality_risk",
)
DEFAULT_SCENARIOS: Final[tuple[str, ...]] = ("무작업", "관수 중심", "방제+적엽", "즉시 수확")


def main() -> None:
    _ = st.set_page_config(page_title="설향 온실 시뮬레이터", layout="wide")
    _ = st.header("설향 온실 시뮬레이터")

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
    _ = st.sidebar.header("초기 온실 상태")
    return GreenhouseState(
        substrate_moisture_pct=st.sidebar.slider("배지수분 (%)", 30.0, 90.0, 56.0, 1.0),
        drain_ec=st.sidebar.slider("배액 EC", 0.8, 3.5, 1.8, 0.1),
        disease_risk=st.sidebar.slider("병해 위험", 0.0, 1.0, 0.42, 0.01),
        ripe_fruit_ratio=st.sidebar.slider("익은 과실 비율", 0.0, 1.0, 0.62, 0.01),
        fruit_count=st.sidebar.slider("과실 수", 20, 180, 95, 1),
        leaf_density=st.sidebar.slider("엽밀도", 0.2, 1.0, 0.78, 0.01),
        ventilation_score=st.sidebar.slider("환기 점수", 0.0, 1.0, 0.36, 0.01),
        yield_potential=st.sidebar.slider("수량 잠재력", 0.5, 1.3, 1.0, 0.01),
        marketable_yield_kg=0.0,
        quality_risk=st.sidebar.slider("품질 위험", 0.0, 1.0, 0.14, 0.01),
        coloring_pct=st.sidebar.slider("착색률 (%)", 50.0, 100.0, 82.0, 1.0),
        distribution_type=DistributionType.ROOM_TEMP,
        old_or_diseased_leaf_level=st.sidebar.slider("노엽/병든 잎 수준", 0.0, 1.0, 0.45, 0.01),
    )


def _environment_controls() -> GreenhouseEnvironment:
    _ = st.sidebar.header("환경 조건")
    return GreenhouseEnvironment(
        solar_radiation_w_m2=st.sidebar.slider("일사량 (W/m2)", 100.0, 900.0, 520.0, 10.0),
        vpd_kpa=st.sidebar.slider("VPD (kPa)", 0.1, 2.0, 0.38, 0.01),
        humidity_pct=st.sidebar.slider("습도 (%)", 45.0, 100.0, 89.0, 1.0),
        rain_probability=st.sidebar.slider("강우 확률 (%)", 0.0, 100.0, 55.0, 1.0),
        inside_temperature_c=st.sidebar.slider("온실 내부 온도 (C)", 12.0, 35.0, 25.0, 0.5),
        leaf_wetness_hours=st.sidebar.slider("엽면젖음 시간", 0.0, 12.0, 5.0, 0.5),
    )


def _scenario_controls(
    state: GreenhouseState,
    environment: GreenhouseEnvironment,
    days: int,
) -> tuple[Scenario, ...]:
    _ = st.sidebar.header("작업 강도")
    irrigation_volume = st.sidebar.slider("관수량 (L)", 0.0, 3.0, 1.2, 0.1)
    control_effectiveness = st.sidebar.slider("방제 효과", 0.0, 1.0, 0.55, 0.01)
    harvest_ratio = st.sidebar.slider("수확 비율", 0.0, 1.0, 0.45, 0.01)
    pruning_ratio = st.sidebar.slider("적엽 비율", 0.0, 0.5, 0.18, 0.01)

    scenario_options = {
        "무작업": (),
        "관수 중심": (
            ScheduledWork(day=1, work=IrrigationWork(volume_l=irrigation_volume)),
            ScheduledWork(day=3, work=IrrigationWork(volume_l=irrigation_volume * 0.7)),
        ),
        "방제+적엽": (
            ScheduledWork(day=1, work=DiseaseControlWork(effectiveness=control_effectiveness)),
            ScheduledWork(day=2, work=LeafPruningWork(removal_ratio=pruning_ratio)),
        ),
        "즉시 수확": (
            ScheduledWork(day=1, work=HarvestWork(pick_ratio=harvest_ratio)),
        ),
        "수확 지연": (
            ScheduledWork(day=min(3, days), work=HarvestWork(pick_ratio=harvest_ratio, delayed_days=2)),
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
    _ = st.subheader("최종 상태")
    columns = st.columns(min(4, len(end_states)))
    for column, record in zip(columns, end_states, strict=False):
        with column:
            _ = st.metric(record.scenario, f"{record.marketable_yield_kg:.2f} kg")
            summary = (
                f"병해 {record.disease_risk:.2f} · 품질 {record.quality_risk:.2f} · 수분 "
                f"{record.substrate_moisture_pct:.1f}%"
            )
            _ = st.caption(summary)


def _render_chart(
    timeline: tuple[SimulationRecord, ...],
    selected_metrics: tuple[str, ...],
) -> None:
    _ = st.subheader("일별 변화")
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
    summary_tab, evidence_tab = st.tabs(("요약 테이블", "근거 로그"))
    with summary_tab:
        _ = st.dataframe(_summary_rows(end_states), use_container_width=True, hide_index=True)
    with evidence_tab:
        _ = st.dataframe(_evidence_rows(evidence_log), use_container_width=True, hide_index=True)


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
