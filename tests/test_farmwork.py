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

        self.assertEqual([task.work_type for task in plan.tasks], [FarmWorkType.IRRIGATION])
        alert_types = [task.work_type for task in plan.auxiliary_alerts]
        self.assertIn(FarmWorkType.DISEASE_CONTROL, alert_types)
        self.assertIn(FarmWorkType.HARVEST, alert_types)
        self.assertIn(FarmWorkType.LEAF_PRUNING, alert_types)
        self.assertIn("보조 알림", plan.summary)
        self.assertNotIn("우선 작업", plan.summary)
        self.assertIn("생육단계", plan.data_sources)
        self.assertIn("이미지/예찰", plan.data_sources)
        self.assertIn("작업이력", plan.data_sources)

        disease = next(task for task in plan.auxiliary_alerts if task.work_type == FarmWorkType.DISEASE_CONTROL)
        self.assertIn("환경 위험 proxy", disease.reason)
        self.assertNotIn("prediction", disease.reason.lower())
        self.assertIn("scouting", " ".join(disease.safeguards).lower())

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
        leaf_alerts = [
            task for task in plan.auxiliary_alerts
            if task.work_type == FarmWorkType.LEAF_PRUNING
        ]

        self.assertEqual(leaf_tasks, [])
        self.assertEqual(leaf_alerts, [])

    def test_harvest_alert_requires_growth_or_image_evidence(self):
        context = FarmWorkContext(
            growth_stage=CropGrowthStage.VEGETATIVE,
            snapshot=GreenhouseSnapshot(
                inside_temperature_c=29.0,
                inside_humidity_pct=70.0,
                image=ImageGrowthSignals(),
            ),
            history=FarmWorkHistory(days_since_harvest=5),
        )

        plan = DailyFarmWorkDecisionEngine().plan_today(context)

        self.assertNotIn(
            FarmWorkType.HARVEST,
            [task.work_type for task in plan.auxiliary_alerts],
        )

    def test_high_humidity_low_vpd_keeps_disease_alert_auxiliary(self):
        context = FarmWorkContext(
            growth_stage=CropGrowthStage.FLOWERING,
            snapshot=GreenhouseSnapshot(
                inside_temperature_c=23.0,
                inside_humidity_pct=94.0,
                vent_open_pct=4.0,
            ),
            history=FarmWorkHistory(days_since_scouting=6),
        )

        plan = DailyFarmWorkDecisionEngine().plan_today(context)

        self.assertNotIn(FarmWorkType.DISEASE_CONTROL, [task.work_type for task in plan.tasks])
        disease = next(task for task in plan.auxiliary_alerts if task.work_type == FarmWorkType.DISEASE_CONTROL)
        self.assertIn("환기", disease.reason)
        self.assertIn("예찰", disease.title)
        self.assertNotIn("actual disease prediction", disease.reason)


if __name__ == "__main__":
    unittest.main()
