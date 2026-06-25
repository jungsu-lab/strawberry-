import unittest

from libsbapi.display_labels import (
    ACTION_LABELS_KO,
    AUXILIARY_ALERT_LABELS_KO,
    DASHBOARD_SAFETY_TEXT,
    SECTION_TITLES_KO,
    STATUS_LABELS_KO,
    VARIABLE_LABELS_KO,
    action_label,
    status_label,
)


class DisplayLabelsTest(unittest.TestCase):
    def test_level1_action_labels_are_presentation_ready_korean(self) -> None:
        self.assertEqual(ACTION_LABELS_KO["irrigation"], "관수")
        self.assertEqual(ACTION_LABELS_KO["nutrient_ec_check"], "EC·양액 조절")
        self.assertEqual(ACTION_LABELS_KO["ventilation_dehumidification"], "환기")
        self.assertEqual(ACTION_LABELS_KO["shading_high_temperature"], "차광")
        self.assertEqual(ACTION_LABELS_KO["heating_low_temperature"], "보온 또는 난방 검토")

    def test_level2_alert_labels_are_separate_auxiliary_alerts(self) -> None:
        self.assertEqual(AUXILIARY_ALERT_LABELS_KO["disease_environment_risk_proxy"], "병해 위험 예찰 알림")
        self.assertEqual(AUXILIARY_ALERT_LABELS_KO["harvest_monitoring"], "수확 가능성 알림")
        self.assertEqual(AUXILIARY_ALERT_LABELS_KO["leaf_removal_caution"], "적엽 검토 알림")

    def test_status_and_variable_labels_are_natural_korean(self) -> None:
        self.assertEqual(status_label("recommend"), "추천")
        self.assertEqual(status_label("caution"), "주의")
        self.assertEqual(VARIABLE_LABELS_KO["humidity"], "습도")
        self.assertEqual(VARIABLE_LABELS_KO["rain_probability"], "강우 확률")

    def test_dashboard_sections_and_safety_text_are_fixed(self) -> None:
        expected_sections = {
            "오늘의 추천 요약",
            "현재 상태",
            "1~3시간 예상 상태",
            "Level 1 작업 비교",
            "필요도 점수",
            "Level 2 보조 알림",
            "시뮬레이션 최종 상태",
            "일별 변화",
            "요약표",
        }

        self.assertTrue(expected_sections <= set(SECTION_TITLES_KO.values()))
        self.assertIn("decision_support", DASHBOARD_SAFETY_TEXT)
        self.assertIn("사람 검토 필요", DASHBOARD_SAFETY_TEXT)
        self.assertIn("자율제어 아님", DASHBOARD_SAFETY_TEXT)

    def test_unknown_action_keeps_internal_id(self) -> None:
        self.assertEqual(action_label("new_internal_id"), "new_internal_id")


if __name__ == "__main__":
    unittest.main()
