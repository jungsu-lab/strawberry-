import unittest

from libsbapi.berrynext import (
    BerryNextDecisionEngine,
    GreenhouseSnapshot,
    ImageGrowthSignals,
    WeatherForecast,
    compute_vpd_kpa,
)


class BerryNextDecisionEngineTest(unittest.TestCase):
    def test_compute_vpd(self):
        vpd = compute_vpd_kpa(25, 70)
        self.assertGreater(vpd, 0.9)
        self.assertLess(vpd, 1.1)

    def test_recommendations_are_ranked_by_score(self):
        engine = BerryNextDecisionEngine()
        snapshot = GreenhouseSnapshot(
            inside_temperature_c=26,
            inside_humidity_pct=90,
            root_zone_moisture_pct=32,
            solar_radiation_w_m2=500,
            ec=1.5,
            ph=6.0,
            vent_open_pct=5,
            weather=WeatherForecast(rain_probability=80, expected_rain_mm=8),
            image=ImageGrowthSignals(
                ripe_fruit_ratio=0.85,
                average_fruit_size_mm=30,
                fruit_count=42,
            ),
        )

        recommendations = engine.recommend(snapshot)

        self.assertEqual(len(recommendations), 3)
        self.assertGreaterEqual(recommendations[0].score, recommendations[1].score)
        self.assertGreaterEqual(recommendations[1].score, recommendations[2].score)

    def test_over_wet_root_zone_delays_irrigation(self):
        engine = BerryNextDecisionEngine()
        snapshot = GreenhouseSnapshot(
            inside_temperature_c=20,
            inside_humidity_pct=92,
            root_zone_moisture_pct=82,
        )

        irrigation = engine.irrigation.recommend(snapshot)

        self.assertEqual(irrigation.action, "delay_irrigation")
        self.assertIn("avoid extra irrigation while over-wet", irrigation.safeguards)


if __name__ == "__main__":
    unittest.main()
