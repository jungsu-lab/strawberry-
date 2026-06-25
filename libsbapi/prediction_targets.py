from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from libsbapi.decision_contract import PredictionResult


ACTION_PREDICTION_TARGETS: Final[Mapping[str, frozenset[str]]] = {
    "irrigation": frozenset(
        {
            "substrate_moisture_pct",
            "substrate_moisture",
            "root_zone_moisture_pct",
            "root_zone_moisture",
            "vpd_kpa",
            "vpd",
            "radiation_w_m2",
            "solar_radiation",
            "cumulative_radiation_j_cm2",
            "cumulative_solar_radiation",
        }
    ),
    "nutrient_ec_check": frozenset(
        {"root_zone_ec", "root_ec", "drainage_ec", "drain_ec", "feed_ec", "substrate_ec", "ec"}
    ),
    "ph_check": frozenset({"root_zone_ph", "drainage_ph", "feed_ph", "ph"}),
    "ventilation_dehumidification": frozenset(
        {"humidity_pct", "humidity", "vpd_kpa", "vpd", "temperature_c", "air_temp", "leaf_wetness_hours"}
    ),
    "shading_high_temperature": frozenset(
        {
            "temperature_c",
            "air_temp",
            "vpd_kpa",
            "vpd",
            "radiation_w_m2",
            "solar_radiation",
            "cumulative_radiation_j_cm2",
            "cumulative_solar_radiation",
        }
    ),
    "heating_low_temperature": frozenset({"temperature_c", "air_temp", "outside_temperature_c", "outside_temp"}),
    "disease_environment_risk_proxy": frozenset(
        {"humidity_pct", "humidity", "vpd_kpa", "vpd", "rain_probability_pct", "leaf_wetness_hours"}
    ),
    "harvest_monitoring": frozenset(
        {"ripe_fruit_ratio", "fruit_count", "coloring_pct", "temperature_c"}
    ),
    "leaf_removal_caution": frozenset({"leaf_density", "humidity_pct"}),
}


def prediction_relates_to_action(action_type: str, prediction: PredictionResult) -> bool:
    return prediction.target in ACTION_PREDICTION_TARGETS.get(action_type, frozenset())
