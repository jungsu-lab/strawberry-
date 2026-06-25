import subprocess
import sys
import unittest


class GreenhouseScenarioCompareExampleTest(unittest.TestCase):
    def test_example_displays_level1_candidate_labels_first(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "examples.greenhouse_scenario_compare"],
            check=True,
            capture_output=True,
            text=True,
        )

        output = result.stdout
        self.assertIn("단기 Level 1 온실 관리 작업 시나리오 비교", output)
        self.assertIn("무작업 / 유지", output)
        self.assertIn("EC·양액 조절", output)
        self.assertIn("환기", output)
        self.assertIn("차광", output)
        self.assertIn("보온", output)
        self.assertNotIn("no_ventilation |", output)
        self.assertNotIn("no_shading |", output)


if __name__ == "__main__":
    unittest.main()
