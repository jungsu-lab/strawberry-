import subprocess
import sys
import unittest

from dashboard.greenhouse_dashboard import _prediction_rows
from libsbapi.decision_contract import CurrentGreenhouseState
from libsbapi.environmental_prediction import GAMReadyPredictor, NoChangeBaselinePredictor


class PredictionBaselineContractTest(unittest.TestCase):
    def test_no_change_baseline_contract_is_explicit(self) -> None:
        state = CurrentGreenhouseState(air_temp=27.5, humidity=91.0, vpd=0.33)

        predictions = NoChangeBaselinePredictor().predict(state, horizons=(1,))
        by_target = {prediction.target: prediction for prediction in predictions}
        air_temp = by_target["air_temp"]

        self.assertEqual(air_temp.model_used, "no_change_baseline")
        self.assertEqual(air_temp.predicted_delta, 0.0)
        self.assertEqual(air_temp.predicted_value, air_temp.current_value)
        self.assertTrue(air_temp.fallback_used)
        self.assertIn("baseline", air_temp.fallback_reason)

    def test_dashboard_prediction_rows_show_baseline_and_zero_delta(self) -> None:
        prediction = NoChangeBaselinePredictor().predict(CurrentGreenhouseState(humidity=91.0), horizons=(1,))[0]

        rows = _prediction_rows((prediction,))

        self.assertEqual(rows[0]["예측 변화량"], "0.00")
        self.assertEqual(rows[0]["model_used"], "no_change_baseline")
        self.assertTrue(rows[0]["fallback_used"])
        self.assertIn("baseline", rows[0]["fallback_reason"])

    def test_offline_example_says_baseline_and_future_gam_not_active(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "examples.berrynext_today_recommendation"],
            check=True,
            capture_output=True,
            text=True,
        )

        output = result.stdout
        self.assertIn("기준선", output)
        self.assertIn("GAM은 향후", output)
        self.assertIn("no_change_baseline", output)
        self.assertNotIn("GAM 예측 활성", output)
        self.assertNotIn("real GAM", output)

    def test_gam_ready_predictor_is_not_implemented(self) -> None:
        with self.assertRaises(NotImplementedError):
            GAMReadyPredictor().predict(CurrentGreenhouseState(air_temp=24.0), horizons=(1,))


if __name__ == "__main__":
    unittest.main()
