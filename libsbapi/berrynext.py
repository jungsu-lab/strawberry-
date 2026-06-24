#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#

"""BerryNext AI decision helpers for strawberry smart-farm MVPs.

This module intentionally starts with transparent rule-based logic. Predictive
models can later feed the same inputs or replace individual score functions.
"""

from dataclasses import dataclass, field
from math import exp
from typing import Dict, List, Optional


@dataclass
class WeatherForecast:
    rain_probability: Optional[float] = None
    expected_rain_mm: Optional[float] = None
    min_temperature_c: Optional[float] = None
    max_temperature_c: Optional[float] = None
    solar_radiation_mj: Optional[float] = None


@dataclass
class ImageGrowthSignals:
    ripe_fruit_ratio: Optional[float] = None
    average_fruit_size_mm: Optional[float] = None
    fruit_count: Optional[int] = None
    leaf_density: Optional[float] = None
    disease_spot_ratio: Optional[float] = None


@dataclass
class GreenhouseSnapshot:
    inside_temperature_c: Optional[float] = None
    inside_humidity_pct: Optional[float] = None
    co2_ppm: Optional[float] = None
    solar_radiation_w_m2: Optional[float] = None
    root_zone_moisture_pct: Optional[float] = None
    ec: Optional[float] = None
    ph: Optional[float] = None
    supply_ml: Optional[float] = None
    drain_ml: Optional[float] = None
    vent_open_pct: Optional[float] = None
    fog_on: Optional[bool] = None
    heating_on: Optional[bool] = None
    energy_kwh_today: Optional[float] = None
    weather: WeatherForecast = field(default_factory=WeatherForecast)
    image: ImageGrowthSignals = field(default_factory=ImageGrowthSignals)


@dataclass
class Recommendation:
    action: str
    priority: str
    score: float
    reason: str
    safeguards: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


def compute_vpd_kpa(temperature_c: Optional[float], humidity_pct: Optional[float]) -> Optional[float]:
    """Compute vapor pressure deficit in kPa."""
    if temperature_c is None or humidity_pct is None:
        return None
    if not 0 <= humidity_pct <= 100:
        raise ValueError("humidity_pct must be between 0 and 100")

    saturated_vapor_pressure = 0.6108 * exp((17.27 * temperature_c) / (temperature_c + 237.3))
    actual_vapor_pressure = saturated_vapor_pressure * humidity_pct / 100.0
    return max(0.0, saturated_vapor_pressure - actual_vapor_pressure)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _priority(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


class IrrigationDecisionEngine:
    """Recommend irrigation and nutrient actions from greenhouse signals."""

    def recommend(self, snapshot: GreenhouseSnapshot) -> Recommendation:
        vpd = compute_vpd_kpa(snapshot.inside_temperature_c, snapshot.inside_humidity_pct)
        score = 0.0
        reasons = []
        safeguards = []
        moisture_is_low = False

        if snapshot.root_zone_moisture_pct is not None:
            if snapshot.root_zone_moisture_pct < 35:
                moisture_is_low = True
                score += 0.35
                reasons.append("root-zone moisture is low")
            elif snapshot.root_zone_moisture_pct > 75:
                score -= 0.35
                reasons.append("root-zone moisture is already high")
                safeguards.append("avoid extra irrigation while over-wet")

        if vpd is not None:
            if vpd > 1.2:
                score += 0.25
                reasons.append("VPD indicates high water demand")
            elif vpd < 0.35 and not moisture_is_low:
                score -= 0.2
                reasons.append("low VPD raises over-wet disease risk")
                safeguards.append("prefer ventilation before irrigation")

        if snapshot.solar_radiation_w_m2 is not None and snapshot.solar_radiation_w_m2 > 450:
            score += 0.2
            reasons.append("solar radiation supports higher transpiration")

        if snapshot.ec is not None:
            if snapshot.ec > 2.2:
                score += 0.1
                reasons.append("EC is high enough to check drain ratio")
                safeguards.append("do not raise nutrient concentration before drain check")
            elif snapshot.ec < 0.8:
                score += 0.1
                reasons.append("EC is low and nutrient adjustment may be needed")

        if snapshot.ph is not None and not 5.5 <= snapshot.ph <= 6.5:
            score += 0.1
            reasons.append("pH is outside the preferred range")
            safeguards.append("correct pH gradually")

        score = _clamp(score)
        action = "increase_or_schedule_irrigation" if score >= 0.45 else "maintain_irrigation"
        if snapshot.root_zone_moisture_pct is not None and snapshot.root_zone_moisture_pct > 75:
            action = "delay_irrigation"

        return Recommendation(
            action=action,
            priority=_priority(score),
            score=round(score, 3),
            reason=", ".join(reasons) or "no strong irrigation signal",
            safeguards=safeguards,
            metrics={"vpd_kpa": round(vpd, 3)} if vpd is not None else {},
        )


class DiseaseRiskDecisionEngine:
    """Estimate disease risk and recommend prevention-oriented actions."""

    def recommend(self, snapshot: GreenhouseSnapshot) -> Recommendation:
        vpd = compute_vpd_kpa(snapshot.inside_temperature_c, snapshot.inside_humidity_pct)
        score = 0.0
        reasons = []
        safeguards = []

        if snapshot.inside_humidity_pct is not None and snapshot.inside_humidity_pct >= 85:
            score += 0.3
            reasons.append("inside humidity is high")

        if vpd is not None and vpd < 0.35:
            score += 0.25
            reasons.append("low VPD suggests wet canopy conditions")

        if snapshot.weather.rain_probability is not None and snapshot.weather.rain_probability >= 60:
            score += 0.2
            reasons.append("rain forecast increases disease pressure")

        if snapshot.weather.expected_rain_mm is not None and snapshot.weather.expected_rain_mm >= 5:
            score += 0.15
            reasons.append("meaningful rainfall is expected")

        if snapshot.vent_open_pct is not None and snapshot.vent_open_pct < 15:
            score += 0.1
            reasons.append("ventilation is limited")

        if snapshot.fog_on:
            score += 0.1
            safeguards.append("avoid fogging while disease risk is high")

        if snapshot.image.disease_spot_ratio is not None and snapshot.image.disease_spot_ratio >= 0.03:
            score += 0.25
            reasons.append("image signal suggests visible disease spots")

        score = _clamp(score)
        action = "monitor"
        if score >= 0.75:
            action = "prioritize_scouting_and_prepare_control"
        elif score >= 0.45:
            action = "increase_ventilation_and_scout"

        return Recommendation(
            action=action,
            priority=_priority(score),
            score=round(score, 3),
            reason=", ".join(reasons) or "disease risk is not elevated",
            safeguards=safeguards,
            metrics={"vpd_kpa": round(vpd, 3)} if vpd is not None else {},
        )


class HarvestDecisionEngine:
    """Recommend harvest timing from image and environment signals."""

    def recommend(self, snapshot: GreenhouseSnapshot) -> Recommendation:
        score = 0.0
        reasons = []

        if snapshot.image.ripe_fruit_ratio is not None:
            if snapshot.image.ripe_fruit_ratio >= 0.8:
                score += 0.45
                reasons.append("ripe fruit ratio is high")
            elif snapshot.image.ripe_fruit_ratio >= 0.6:
                score += 0.25
                reasons.append("ripe fruit ratio is rising")

        if snapshot.image.average_fruit_size_mm is not None and snapshot.image.average_fruit_size_mm >= 28:
            score += 0.2
            reasons.append("fruit size is in harvestable range")

        if snapshot.image.fruit_count is not None and snapshot.image.fruit_count >= 30:
            score += 0.15
            reasons.append("visible fruit count is sufficient")
        elif snapshot.image.fruit_count is not None and snapshot.image.fruit_count > 0:
            score += 0.15
            reasons.append("fruit set indicates harvest monitoring window")

        if snapshot.weather.rain_probability is not None and snapshot.weather.rain_probability >= 60:
            score += 0.1
            reasons.append("rain forecast may reduce quality if delayed")

        if snapshot.inside_temperature_c is not None and snapshot.inside_temperature_c >= 28:
            score += 0.1
            reasons.append("high temperature can accelerate quality loss")

        score = _clamp(score)
        action = "harvest_today" if score >= 0.65 else "wait_and_monitor"

        return Recommendation(
            action=action,
            priority=_priority(score),
            score=round(score, 3),
            reason=", ".join(reasons) or "harvest signal is not strong yet",
        )


class BerryNextDecisionEngine:
    """Bundle the three MVP engines: irrigation, disease, and harvest."""

    def __init__(self):
        self.irrigation = IrrigationDecisionEngine()
        self.disease = DiseaseRiskDecisionEngine()
        self.harvest = HarvestDecisionEngine()

    def recommend(self, snapshot: GreenhouseSnapshot) -> List[Recommendation]:
        recommendations = [
            self.irrigation.recommend(snapshot),
            self.disease.recommend(snapshot),
            self.harvest.recommend(snapshot),
        ]
        return sorted(recommendations, key=lambda item: item.score, reverse=True)
