import json
import unittest
from pathlib import Path

from libsbapi.berrynext import GreenhouseSnapshot as LegacyGreenhouseSnapshot
from libsbapi.current_state_builder import CurrentStateBuilder
from libsbapi.farmwork import CropGrowthStage, FarmWorkContext


class CurrentStateBuilderTest(unittest.TestCase):
    def test_builds_current_state_from_sample_daily_context_json(self) -> None:
        state = CurrentStateBuilder().from_daily_context_file(Path("examples/sample_daily_context.json"))

        self.assertEqual(state.air_temp, 27.5)
        self.assertEqual(state.humidity, 91.0)
        self.assertEqual(state.co2, 620.0)
        self.assertEqual(state.solar_radiation, 540.0)
        self.assertEqual(state.root_zone_moisture, 31.0)
        self.assertEqual(state.drain_ec, 1.3)
        self.assertEqual(state.drain_ph, 6.0)
        self.assertEqual(state.growth_stage, "harvest")
        self.assertIn("sample_daily_context", state.source_labels)
        self.assertIn("timestamp", state.missing_fields)

    def test_calculates_vpd_when_missing_but_temperature_and_humidity_exist(self) -> None:
        payload = {
            "timestamp": "2026-06-25T09:00:00+09:00",
            "growth_stage": "fruiting",
            "snapshot": {
                "inside_temperature_c": 25.0,
                "inside_humidity_pct": 80.0,
            },
        }

        state = CurrentStateBuilder().from_daily_context(payload, source_label="unit_test")

        self.assertIsNotNone(state.vpd)
        self.assertAlmostEqual(state.vpd or 0.0, 0.634, places=3)
        self.assertIn("vpd", state.fallback_fields)

    def test_records_missing_moisture_and_ec_as_quality_warnings(self) -> None:
        payload = {
            "timestamp": "2026-06-25T09:00:00+09:00",
            "snapshot": {
                "inside_temperature_c": 22.0,
                "inside_humidity_pct": 70.0,
            },
        }

        state = CurrentStateBuilder().from_daily_context(payload, source_label="unit_test")

        self.assertIn("root_zone_moisture", state.missing_fields)
        self.assertIn("drain_ec", state.missing_fields)
        self.assertIn("root_zone_moisture missing", state.quality_warnings)
        self.assertIn("drain_ec missing", state.quality_warnings)

    def test_preserves_growth_stage_and_time_of_day_if_present(self) -> None:
        payload = {
            "timestamp": "2026-06-25T15:30:00+09:00",
            "growth_stage": "flowering",
            "time_of_day": "afternoon",
            "snapshot": {},
        }

        state = CurrentStateBuilder().from_daily_context(payload, source_label="unit_test")

        self.assertEqual(state.growth_stage, "flowering")
        self.assertEqual(state.time_of_day, "afternoon")

    def test_does_not_crash_when_optional_fields_are_missing(self) -> None:
        state = CurrentStateBuilder().from_daily_context({"snapshot": {}}, source_label="unit_test")

        self.assertIsNone(state.air_temp)
        self.assertIsNone(state.vpd)
        self.assertIn("air_temp", state.missing_fields)
        self.assertIn("humidity", state.missing_fields)

    def test_zero_values_are_preserved_and_flagged_when_ambiguous(self) -> None:
        payload = {
            "timestamp": "2026-06-25T09:00:00+09:00",
            "snapshot": {
                "inside_temperature_c": 0.0,
                "inside_humidity_pct": 0.0,
                "root_zone_moisture_pct": 0.0,
                "ec": 0.0,
            },
        }

        state = CurrentStateBuilder().from_daily_context(payload, source_label="unit_test")

        self.assertEqual(state.air_temp, 0.0)
        self.assertEqual(state.humidity, 0.0)
        self.assertEqual(state.root_zone_moisture, 0.0)
        self.assertEqual(state.drain_ec, 0.0)
        self.assertIn("humidity is zero; verify sensor validity", state.quality_warnings)
        self.assertIn("root_zone_moisture is zero; verify sensor validity", state.quality_warnings)
        self.assertIn("drain_ec is zero; verify sensor validity", state.quality_warnings)

    def test_builds_from_existing_farmwork_context_and_snapshot(self) -> None:
        snapshot = LegacyGreenhouseSnapshot(
            inside_temperature_c=24.0,
            inside_humidity_pct=82.0,
            root_zone_moisture_pct=45.0,
            ec=1.6,
            ph=6.1,
        )
        context = FarmWorkContext(
            growth_stage=CropGrowthStage.FRUITING,
            snapshot=snapshot,
        )

        from_context = CurrentStateBuilder().from_farmwork_context(context)
        from_snapshot = CurrentStateBuilder().from_greenhouse_snapshot(snapshot)

        self.assertEqual(from_context.growth_stage, "fruiting")
        self.assertEqual(from_context.air_temp, 24.0)
        self.assertEqual(from_snapshot.air_temp, 24.0)
        self.assertIn("farmwork_context", from_context.source_labels)

    def test_builds_from_processed_berrynext_json_like_payload(self) -> None:
        path = Path("/home/jungsu/processed_berrynext/quality_report.json")
        if not path.exists():
            self.skipTest("processed_berrynext quality report is not available")

        report = json.loads(path.read_text(encoding="utf-8"))
        state = CurrentStateBuilder().from_daily_context(
            {"snapshot": report.get("current_state", {})},
            source_label="processed_berrynext",
        )

        self.assertIn("processed_berrynext", state.source_labels)
        self.assertIsNone(state.stale_timestamp)


if __name__ == "__main__":
    unittest.main()
