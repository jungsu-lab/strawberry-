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
        self.assertIn("BerryNext offline decision-support demo", output)
        self.assertIn("1. Current state", output)
        self.assertIn("2. Predicted future state", output)
        self.assertIn("3. Scenario comparison summary", output)
        self.assertIn("4. Literature/manual rule checks", output)
        self.assertIn("5. Work-need scores", output)
        self.assertIn("6. Level 1 ranked recommendations", output)
        self.assertIn("7. Level 2 auxiliary alerts", output)
        self.assertIn("disease-risk scouting alert", output)
        self.assertIn("harvest possibility alert", output)
        self.assertIn("leaf-removal review alert", output)
        self.assertIn("decision_support", output)
        self.assertIn("human review required", output)
        self.assertIn("GAM planned/future", output)
        self.assertNotIn("autonomous control", output.lower())
        self.assertNotIn("control command", output.lower())


if __name__ == "__main__":
    unittest.main()
