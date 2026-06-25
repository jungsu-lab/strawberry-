import subprocess
import sys
import unittest


class BerryNextTodayRecommendationExampleTest(unittest.TestCase):
    def test_offline_demo_prints_corrected_pipeline_sections(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "examples.berrynext_today_recommendation"],
            check=True,
            capture_output=True,
            text=True,
        )

        output = result.stdout
        self.assertIn("BerryNext 오프라인 의사결정 보조 데모", output)
        self.assertIn("1. 현재 상태", output)
        self.assertIn("2. 1~3시간 예상 상태", output)
        self.assertIn("3. 시나리오 비교 요약", output)
        self.assertIn("4. 문헌/매뉴얼 기준 룰 확인", output)
        self.assertIn("5. 필요도 점수", output)
        self.assertIn("6. Level 1 작업 추천 순위", output)
        self.assertIn("7. Level 2 보조 알림", output)
        self.assertIn("병해 위험 예찰 알림", output)
        self.assertIn("수확 가능성 알림", output)
        self.assertIn("적엽 검토 알림", output)
        self.assertIn("decision_support", output)
        self.assertIn("사람 검토", output)
        self.assertIn("GAM은 향후", output)
        self.assertNotIn("autonomous control", output.lower())
        self.assertNotIn("control command", output.lower())


if __name__ == "__main__":
    unittest.main()
