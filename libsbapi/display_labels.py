from __future__ import annotations

from typing import Final


LEVEL1_ACTION_IDS: Final[tuple[str, ...]] = (
    "irrigation",
    "nutrient_ec_check",
    "ventilation_dehumidification",
    "shading_high_temperature",
    "heating_low_temperature",
)
ACTION_LABELS_KO: Final[dict[str, str]] = {
    "irrigation": "관수",
    "nutrient_ec_check": "EC·양액 조절",
    "ventilation_dehumidification": "환기",
    "shading_high_temperature": "차광",
    "heating_low_temperature": "보온 또는 난방 검토",
}
AUXILIARY_ALERT_LABELS_KO: Final[dict[str, str]] = {
    "disease_environment_risk_proxy": "병해 위험 예찰 알림",
    "harvest_monitoring": "수확 가능성 알림",
    "leaf_removal_caution": "적엽 검토 알림",
    "disease_risk_scouting_alert": "병해 위험 예찰 알림",
    "harvest_possibility_alert": "수확 가능성 알림",
    "leaf_removal_review_alert": "적엽 검토 알림",
}
SCENARIO_LABELS_KO: Final[dict[str, str]] = {
    "no_irrigation": "무작업 / 유지",
    "irrigation": "관수",
    "lower_ec_nutrient_adjustment": "EC·양액 조절",
    "raise_ec_check_supplied_ec": "공급 EC 확인",
    "ventilation": "환기",
    "no_ventilation": "환기 보류",
    "shading": "차광",
    "no_shading": "차광 보류",
    "heat_preservation_heating_review": "보온 또는 난방 검토",
    "no_heat_preservation": "보온 보류",
}
SCORE_COMPONENT_LABELS_KO: Final[dict[str, str]] = {
    "moisture_stress": "수분 스트레스",
    "salinity_stress": "EC·염류 스트레스",
    "high_temp_stress": "고온 스트레스",
    "low_temp_stress": "저온 스트레스",
    "disease_environment_risk": "병해 환경 위험 프록시",
    "energy_cost": "에너지 비용",
}
RISK_LABELS_KO: Final[dict[str, str]] = {
    "condensation": "결로 위험",
    "over_wet_substrate": "배지 과습 위험",
    "salinity": "염류 스트레스 위험",
    "cold_air": "저온 유입 위험",
    "energy": "에너지 비용 증가",
}
SECTION_TITLES_KO: Final[dict[str, str]] = {
    "recommendation_summary": "오늘의 추천 요약",
    "current_state": "현재 상태",
    "prediction": "1~3시간 예상 상태",
    "scenario_comparison": "Level 1 작업 비교",
    "work_need_score": "필요도 점수",
    "auxiliary_alerts": "Level 2 보조 알림",
    "simulation_final_state": "시뮬레이션 최종 상태",
    "daily_change": "일별 변화",
    "summary_table": "요약표",
}
VARIABLE_LABELS_KO: Final[dict[str, str]] = {
    "air_temp": "내부 온도",
    "inside_temperature_c": "내부 온도",
    "humidity": "습도",
    "humidity_pct": "습도",
    "vpd": "VPD",
    "vpd_kpa": "VPD",
    "solar_radiation": "일사량",
    "solar_radiation_w_m2": "일사량",
    "root_zone_moisture": "근권수분",
    "substrate_moisture": "배지수분",
    "substrate_moisture_pct": "배지수분",
    "feed_ec": "급액 EC",
    "drain_ec": "배액 EC",
    "root_ec": "근권 EC",
    "feed_ph": "급액 pH",
    "drain_ph": "배액 pH",
    "outside_temp": "외기 온도",
    "outside_humidity": "외기 습도",
    "rain_probability": "강우 확률",
    "growth_stage": "생육 단계",
    "time_of_day": "시간대",
    "disease_risk": "병해 환경 위험 프록시",
    "ripe_fruit_ratio": "수확 가능성",
    "leaf_density": "엽밀도",
    "ventilation_score": "환기 상태",
    "marketable_yield_kg": "상품 수확량 프록시",
    "quality_risk": "품질 위험 프록시",
}
STATUS_LABELS_KO: Final[dict[str, str]] = {
    "recommend": "추천",
    "caution": "주의",
    "hold": "보류",
    "monitor": "모니터링",
    "review_needed": "검토 필요",
}
DASHBOARD_SAFETY_BADGE: Final = "decision_support · 사람 검토 필요 · 자율제어 아님"
DASHBOARD_SAFETY_TEXT: Final = (
    "decision_support · 사람 검토 필요 · 자율제어 아님\n"
    "권장사항은 자율제어를 실행하지 않으며, 실제 작업 전 온실 상태와 작업 가능 여부를 사람이 확인해야 합니다."
)
AUXILIARY_RESEARCH_WARNING: Final = (
    "이 탭은 방제, 수확, 적엽을 직접 추천하는 핵심 모델이 아니라, "
    "보조 알림 프록시를 확인하기 위한 연구용 화면입니다."
)


def action_label(action_id: str) -> str:
    return ACTION_LABELS_KO.get(action_id, AUXILIARY_ALERT_LABELS_KO.get(action_id, action_id))


def scenario_label(action_id: str) -> str:
    return SCENARIO_LABELS_KO.get(action_id, action_id)


def variable_label(variable_id: str) -> str:
    return VARIABLE_LABELS_KO.get(variable_id, variable_id)


def status_label(status: str) -> str:
    return STATUS_LABELS_KO.get(status, status)
