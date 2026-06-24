import unittest

from libsbapi.action_recommenders import ActionRecommendationEngine
from libsbapi.decision_contract import (
    GreenhouseSnapshot,
    GrowthState,
    NutrientState,
    RootZoneState,
    SensorState,
    WeatherState,
)
from libsbapi.evidence_rules import load_evidence_rules


class ActionRecommendationEngineTest(unittest.TestCase):
    def test_high_vpd_and_low_moisture_suggests_irrigation_check(self) -> None:
        snapshot = _snapshot(
            sensor_state=SensorState(
                temperature_c=29.0,
                humidity_pct=45.0,
                vpd_kpa=1.55,
                radiation_w_m2=720.0,
            ),
            root_zone_state=RootZoneState(substrate_moisture_pct=48.0),
        )

        recommendations = ActionRecommendationEngine(load_evidence_rules()).recommend(snapshot)
        irrigation = _single(recommendations, "irrigation")

        self.assertIn(irrigation.priority, {"medium", "high"})
        self.assertIn("VPD", irrigation.reason)
        self.assertIn("substrate moisture", irrigation.reason)
        self.assertTrue(irrigation.evidence_references)
        self.assertIn("decision_support_only", irrigation.safety_flags)

    def test_high_humidity_and_low_vpd_suggests_ventilation_monitoring(self) -> None:
        snapshot = _snapshot(
            sensor_state=SensorState(
                temperature_c=23.0,
                humidity_pct=91.0,
                vpd_kpa=0.22,
            )
        )

        recommendations = ActionRecommendationEngine(load_evidence_rules()).recommend(snapshot)
        ventilation = _single(recommendations, "ventilation_dehumidification")

        self.assertIn(ventilation.priority, {"medium", "high"})
        self.assertIn("humidity", ventilation.reason)
        self.assertIn("low VPD", ventilation.reason)
        self.assertIn("human review", " ".join(ventilation.risks))

    def test_high_ec_suggests_drainage_and_root_zone_ec_check(self) -> None:
        snapshot = _snapshot(
            root_zone_state=RootZoneState(root_zone_ec=2.7),
            nutrient_state=NutrientState(drainage_ec=2.9, feed_ec=1.4),
        )

        recommendations = ActionRecommendationEngine(load_evidence_rules()).recommend(snapshot)
        ec_check = _single(recommendations, "nutrient_ec_check")

        self.assertIn(ec_check.priority, {"medium", "high"})
        self.assertIn("EC", ec_check.reason)
        self.assertIn("drainage", ec_check.reason)
        self.assertIn("root-zone", ec_check.reason)

    def test_low_temperature_suggests_heating_or_thermal_protection_check(self) -> None:
        snapshot = _snapshot(
            sensor_state=SensorState(temperature_c=9.5, humidity_pct=83.0),
            weather_state=WeatherState(outside_temperature_c=1.0),
            growth_state=GrowthState(growth_stage="flowering"),
        )

        recommendations = ActionRecommendationEngine(load_evidence_rules()).recommend(snapshot)
        heating = _single(recommendations, "heating_low_temperature")

        self.assertIn(heating.priority, {"medium", "high"})
        self.assertIn("low temperature", heating.reason)
        self.assertIn("energy", " ".join(heating.risks))

    def test_leaf_removal_recommendation_is_cautious_not_aggressive(self) -> None:
        snapshot = _snapshot(
            sensor_state=SensorState(humidity_pct=88.0),
            growth_state=GrowthState(growth_stage="fruiting", leaf_density=0.91),
        )

        recommendations = ActionRecommendationEngine(load_evidence_rules()).recommend(snapshot)
        leaf = _single(recommendations, "leaf_removal_caution")

        self.assertEqual(leaf.priority, "medium")
        self.assertIn("cautious", leaf.reason)
        self.assertIn("avoid aggressive", " ".join(leaf.risks))
        self.assertIn("requires_human_review", leaf.safety_flags)

    def test_disease_risk_is_environmental_proxy_only(self) -> None:
        snapshot = _snapshot(
            sensor_state=SensorState(humidity_pct=92.0, vpd_kpa=0.2),
            weather_state=WeatherState(rain_probability_pct=70.0),
            growth_state=GrowthState(disease_spot_ratio=0.04),
        )

        recommendations = ActionRecommendationEngine(load_evidence_rules()).recommend(snapshot)
        disease = _single(recommendations, "disease_environment_risk_proxy")

        self.assertIn("environmental disease risk proxy", disease.reason)
        self.assertIn("not actual disease prediction", " ".join(disease.risks))
        self.assertIn("requires_field_confirmation", disease.safety_flags)


def _snapshot(
    sensor_state: SensorState = SensorState(),
    root_zone_state: RootZoneState = RootZoneState(),
    nutrient_state: NutrientState = NutrientState(),
    weather_state: WeatherState = WeatherState(),
    growth_state: GrowthState = GrowthState(),
) -> GreenhouseSnapshot:
    return GreenhouseSnapshot(
        timestamp="2026-06-25T09:00:00+09:00",
        sensor_state=sensor_state,
        root_zone_state=root_zone_state,
        nutrient_state=nutrient_state,
        weather_state=weather_state,
        growth_state=growth_state,
    )


def _single(
    recommendations: tuple,
    action_type: str,
):
    matches = [item for item in recommendations if item.action_type == action_type]
    if len(matches) != 1:
        raise AssertionError(f"expected one {action_type} recommendation, got {len(matches)}")
    return matches[0]


if __name__ == "__main__":
    unittest.main()
