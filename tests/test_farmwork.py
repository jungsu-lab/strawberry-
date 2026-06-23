import unittest

from libsbapi.farmwork import (
    CropGrowthStage,
    DailyFarmWorkDecisionEngine,
    FarmWorkContext,
    FarmWorkHistory,
    FarmWorkType,
)
from libsbapi.berrynext import GreenhouseSnapshot, ImageGrowthSignals, WeatherForecast


class DailyFarmWorkDecisionEngineTest(unittest.TestCase):
    def test_recommends_today_tasks_from_growth_environment_image_and_history(self):
        context = FarmWorkContext(
            growth_stage=CropGrowthStage.HARVEST,
            snapshot=GreenhouseSnapshot(
                inside_temperature_c=27.5,
                inside_humidity_pct=91.0,
                solar_radiation_w_m2=540.0,
                root_zone_moisture_pct=31.0,
                ec=1.3,
                ph=6.0,
                vent_open_pct=8.0,
                weather=WeatherForecast(rain_probability=75.0, expected_rain_mm=7.0),
                image=ImageGrowthSignals(
                    ripe_fruit_ratio=0.86,
                    average_fruit_size_mm=31.0,
                    fruit_count=52,
                    leaf_density=0.88,
                    disease_spot_ratio=0.04,
                ),
            ),
            history=FarmWorkHistory(
                days_since_irrigation=2,
                days_since_scouting=5,
                days_since_disease_control=11,
                days_since_harvest=3,
                days_since_leaf_pruning=12,
            ),
        )

        plan = DailyFarmWorkDecisionEngine().plan_today(context)

        self.assertEqual(plan.tasks[0].work_type, FarmWorkType.HARVEST)
        self.assertIn(FarmWorkType.DISEASE_CONTROL, [task.work_type for task in plan.tasks])
        self.assertIn(FarmWorkType.IRRIGATION, [task.work_type for task in plan.tasks])
        self.assertIn(FarmWorkType.LEAF_PRUNING, [task.work_type for task in plan.tasks])
        self.assertIn("생육단계", plan.data_sources)
        self.assertIn("이미지/예찰", plan.data_sources)
        self.assertIn("작업이력", plan.data_sources)

    def test_leaf_pruning_is_delayed_when_recently_done(self):
        context = FarmWorkContext(
            growth_stage=CropGrowthStage.FRUITING,
            snapshot=GreenhouseSnapshot(
                inside_temperature_c=24.0,
                inside_humidity_pct=72.0,
                image=ImageGrowthSignals(leaf_density=0.92),
            ),
            history=FarmWorkHistory(days_since_leaf_pruning=2),
        )

        plan = DailyFarmWorkDecisionEngine().plan_today(context)
        leaf_tasks = [
            task for task in plan.tasks
            if task.work_type == FarmWorkType.LEAF_PRUNING
        ]

        self.assertEqual(leaf_tasks, [])


if __name__ == "__main__":
    unittest.main()
