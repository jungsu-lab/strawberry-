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

    def test_primary_recommendations_exclude_auxiliary_alerts(self):
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
        auxiliary_alerts = engine.auxiliary_alerts(snapshot)

        self.assertEqual([item.action for item in recommendations], ["increase_or_schedule_irrigation"])
        self.assertIn("prioritize_disease_risk_scouting", [item.action for item in auxiliary_alerts])
        self.assertIn("harvest_today", [item.action for item in auxiliary_alerts])

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

    def test_low_root_zone_moisture_is_not_suppressed_by_low_vpd(self):
        engine = BerryNextDecisionEngine()
        snapshot = GreenhouseSnapshot(
            inside_temperature_c=26,
            inside_humidity_pct=98,
            root_zone_moisture_pct=18,
        )

        irrigation = engine.irrigation.recommend(snapshot)

        self.assertEqual(irrigation.action, "maintain_irrigation")
        self.assertEqual(irrigation.score, 0.35)
        self.assertNotIn("prefer ventilation before irrigation", irrigation.safeguards)

    def test_visible_fruit_set_creates_harvest_monitoring_signal(self):
        engine = BerryNextDecisionEngine()
        snapshot = GreenhouseSnapshot(image=ImageGrowthSignals(fruit_count=4))

        harvest = engine.harvest.recommend(snapshot)

        self.assertEqual(harvest.score, 0.15)
        self.assertIn("harvest monitoring window", harvest.reason)


if __name__ == "__main__":
    unittest.main()
