import unittest
from pathlib import Path

from examples.build_daily_context import context_from_json_file, plan_from_json_file
from libsbapi import CropGrowthStage, FarmWorkType


class BuildDailyContextTest(unittest.TestCase):
    def test_context_from_json_file_maps_sample_to_engine_input(self):
        sample_path = Path("examples/sample_daily_context.json")

        context = context_from_json_file(sample_path)

        self.assertEqual(context.growth_stage, CropGrowthStage.HARVEST)
        self.assertEqual(context.snapshot.inside_temperature_c, 27.5)
        self.assertEqual(context.snapshot.image.fruit_count, 52)
        self.assertEqual(context.history.days_since_disease_control, 11)

    def test_plan_from_json_file_recommends_daily_work(self):
        sample_path = Path("examples/sample_daily_context.json")

        plan = plan_from_json_file(sample_path)

        work_types = [task.work_type for task in plan.tasks]
        self.assertIn(FarmWorkType.IRRIGATION, work_types)
        self.assertNotIn(FarmWorkType.HARVEST, work_types)
        self.assertNotIn(FarmWorkType.DISEASE_CONTROL, work_types)
        alert_types = [task.work_type for task in plan.auxiliary_alerts]
        self.assertIn(FarmWorkType.HARVEST, alert_types)
        self.assertIn(FarmWorkType.DISEASE_CONTROL, alert_types)


if __name__ == "__main__":
    unittest.main()
