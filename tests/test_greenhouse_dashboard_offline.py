import subprocess
import sys
import unittest
from pathlib import Path

from dashboard.greenhouse_dashboard import (
    LEVEL1_ACTION_LABELS_KO,
    _auxiliary_alert_rows,
    _conflict_notes,
    _prediction_rows,
    _recommendation_summary_rows,
    _state_from_decision_support_inputs,
    _work_score_rows,
)
from libsbapi.decision_contract import CoreRecommendation, CurrentGreenhouseState, PredictionResult, WorkNeedScore
from libsbapi.display_labels import AUXILIARY_RESEARCH_WARNING


class GreenhouseDashboardOfflineTest(unittest.TestCase):
    def test_level1_display_list_contains_only_core_greenhouse_actions(self) -> None:
        self.assertEqual(
            tuple(LEVEL1_ACTION_LABELS_KO),
            (
                "irrigation",
                "nutrient_ec_check",
                "ventilation_dehumidification",
                "shading_high_temperature",
                "heating_low_temperature",
            ),
        )

    def test_korean_labels_exist_for_all_level1_actions(self) -> None:
        self.assertEqual(LEVEL1_ACTION_LABELS_KO["irrigation"], "관수")
        self.assertEqual(LEVEL1_ACTION_LABELS_KO["nutrient_ec_check"], "EC·양액 조절")
        self.assertEqual(LEVEL1_ACTION_LABELS_KO["ventilation_dehumidification"], "환기")
        self.assertEqual(LEVEL1_ACTION_LABELS_KO["shading_high_temperature"], "차광")
        self.assertEqual(LEVEL1_ACTION_LABELS_KO["heating_low_temperature"], "보온 또는 난방 검토")

    def test_level2_alert_rows_are_separate_and_review_oriented(self) -> None:
        rows = _auxiliary_alert_rows((
            _recommendation("harvest_monitoring", 78.0, status="recommend"),
        ))

        self.assertEqual(rows[0]["구분"], "Level 2 보조 알림")
        self.assertEqual(rows[0]["알림"], "수확 가능성 알림")
        self.assertEqual(rows[0]["표시 상태"], "검토 필요")

    def test_harvest_monitoring_is_not_shown_as_core_recommendation(self) -> None:
        rows = _work_score_rows((
            _score("harvest_monitoring", 90.0),
            _score("ventilation_dehumidification", 82.0),
        ))

        self.assertEqual([row["작업"] for row in rows], ["환기"])

    def test_prediction_table_formats_zero_delta_as_number(self) -> None:
        rows = _prediction_rows((
            PredictionResult(
                target="humidity",
                horizon_hours=1,
                current_value=91.0,
                predicted_delta=0.0,
                confidence=0.2,
                model_used="no_change_baseline",
                fallback_used=True,
                fallback_reason="no-change baseline",
            ),
        ))

        self.assertEqual(rows[0]["예측 변화량"], "0.00")
        self.assertEqual(rows[0]["fallback_reason"], "no-change baseline")

    def test_conflict_note_when_irrigation_and_ventilation_recommended_under_low_vpd(self) -> None:
        notes = _conflict_notes(
            (
                _recommendation("ventilation_dehumidification", 82.0),
                _recommendation("irrigation", 76.0),
            ),
            CurrentGreenhouseState(humidity=91.0, vpd=0.33),
        )

        self.assertTrue(any("환기" in note and "관수" in note for note in notes))

    def test_recommendation_summary_only_contains_level1_actions(self) -> None:
        rows = _recommendation_summary_rows((
            _recommendation("disease_environment_risk_proxy", 90.0),
            _recommendation("irrigation", 76.0),
        ))

        self.assertEqual([row["작업"] for row in rows], ["관수"])

    def test_legacy_tab_text_marks_auxiliary_research_proxy(self) -> None:
        source = Path("dashboard/greenhouse_dashboard.py").read_text(encoding="utf-8")

        self.assertIn("보조 알림 시뮬레이션", source)
        self.assertIn("AUXILIARY_RESEARCH_WARNING", source)
        self.assertIn("보조 알림 프록시를 확인하기 위한 연구용 화면", AUXILIARY_RESEARCH_WARNING)

    def test_known_bad_korean_strings_do_not_appear_in_dashboard_source(self) -> None:
        source = Path("dashboard/greenhouse_dashboard.py").read_text(encoding="utf-8")
        bad_strings = (
            "경찰",
            "결정팀",
            "레슬링",
            "통풍구",
            "운동",
            "관수센터",
            "강우 재미",
            "정말",
            "알림을 위한 알림",
            "상태가 최종임",
            "일별 입장",
            "사용자 로그인",
        )

        for bad_string in bad_strings:
            self.assertNotIn(bad_string, source)

    def test_dashboard_does_not_depend_on_examples_package(self) -> None:
        source = Path("dashboard/greenhouse_dashboard.py").read_text(encoding="utf-8")

        self.assertNotIn("from examples.", source)
        self.assertNotIn("import examples.", source)

    def test_dashboard_script_handles_missing_streamlit_gracefully(self) -> None:
        fake_streamlit = Path("/tmp/fake_streamlit_dashboard_test")
        fake_streamlit.mkdir(exist_ok=True)
        (fake_streamlit / "streamlit.py").write_text(
            'raise ModuleNotFoundError("No module named streamlit")\n',
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, "dashboard/greenhouse_dashboard.py"],
            check=True,
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(fake_streamlit)},
        )

        output = result.stdout + result.stderr
        self.assertIn("Streamlit is optional for the offline dashboard", output)
        self.assertIn("pip install streamlit", output)

    def test_decision_support_input_state_can_drive_main_pipeline(self) -> None:
        state = _state_from_decision_support_inputs(
            air_temp=24.0,
            humidity=70.0,
            vpd=0.8,
            solar_radiation=300.0,
            root_zone_moisture=59.0,
            drain_ec=1.4,
            root_ec=None,
            feed_ec=None,
            feed_ph=5.8,
            drain_ph=6.1,
            outside_temp=12.0,
            outside_humidity=74.0,
            co2=430.0,
            growth_stage="수확기",
            time_of_day="오전",
        )

        self.assertEqual(state.root_zone_moisture, 59.0)
        self.assertEqual(state.growth_stage, "harvest")
        self.assertEqual(state.time_of_day, "morning")
        self.assertEqual(state.feed_ph, 5.8)
        self.assertEqual(state.drain_ph, 6.1)
        self.assertEqual(state.outside_temp, 12.0)
        self.assertEqual(state.outside_humidity, 74.0)
        self.assertEqual(state.co2, 430.0)
        self.assertEqual(state.source_labels, ("dashboard_sidebar",))

    def test_sidebar_source_uses_final_recommendation_input_structure(self) -> None:
        source = Path("dashboard/greenhouse_dashboard.py").read_text(encoding="utf-8")

        expected_sections = (
            "오늘 추천 파이프라인 입력",
            "1. 생육 단계 / 시간 정보",
            "2. Level 1 핵심 온실 상태",
            "3. 외부 환경 / 예측 보조",
            "4. 선택 입력: Level 2 보조 알림",
        )
        for section in expected_sections:
            self.assertIn(section, source)

        expected_labels = (
            "생육 단계",
            "시간대",
            "낮/밤 여부",
            "내부 온도 (℃)",
            "습도 (%)",
            "VPD (kPa)",
            "일사량 (W/m²)",
            "배지/근권수분 (%)",
            "급액 EC",
            "배액 EC",
            "근권 EC",
            "pH",
            "외기 온도 (℃)",
            "외기 습도 (%)",
            "강우 확률 (%)",
            "엽면젖음 시간",
            "CO₂",
            "병해 예찰 위험",
            "수확 가능성",
            "착색률",
            "과실 수",
            "엽밀도",
            "노엽/병든 잎 수준",
            "품질 위험",
        )
        for label in expected_labels:
            self.assertIn(label, source)

    def test_sidebar_source_does_not_use_temporary_or_ambiguous_input_labels(self) -> None:
        source = Path("dashboard/greenhouse_dashboard.py").read_text(encoding="utf-8")
        ambiguous_labels = (
            "추천용",
            "Level 1 온실 관리 입력",
            "환경 조건",
            "작업 조건",
            "수량 잠재력 프록시",
            "수확 가능성 점검 비율",
            "적엽 검토 비율",
        )

        for label in ambiguous_labels:
            self.assertNotIn(label, source)


def _score(action_type: str, score: float) -> WorkNeedScore:
    return WorkNeedScore(
        action_type=action_type,
        score=score,
        priority_rank=1,
        confidence=0.56,
        requires_human_review=True,
    )


def _recommendation(action: str, score: float, *, status: str = "recommend") -> CoreRecommendation:
    return CoreRecommendation(
        action=action,
        score=score,
        priority="high",
        status=status,
        reasons=("테스트 이유",),
        requires_human_review=True,
        mode="decision_support",
    )


if __name__ == "__main__":
    unittest.main()
