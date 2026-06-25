import subprocess
import sys
import unittest
from pathlib import Path


class GreenhouseDashboardOfflineTest(unittest.TestCase):
    def test_dashboard_does_not_depend_on_examples_package(self) -> None:
        source = Path("dashboard/greenhouse_dashboard.py").read_text(encoding="utf-8")

        self.assertNotIn("from examples.", source)
        self.assertNotIn("import examples.", source)

    def test_dashboard_script_handles_missing_streamlit_gracefully(self) -> None:
        result = subprocess.run(
            [sys.executable, "dashboard/greenhouse_dashboard.py"],
            check=True,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr
        self.assertIn("Streamlit is optional for the offline dashboard", output)
        self.assertIn("pip install streamlit", output)


if __name__ == "__main__":
    unittest.main()
