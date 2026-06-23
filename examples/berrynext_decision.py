#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#

from libsbapi import BerryNextDecisionEngine, GreenhouseSnapshot, ImageGrowthSignals, WeatherForecast


def main():
    snapshot = GreenhouseSnapshot(
        inside_temperature_c=26.0,
        inside_humidity_pct=88.0,
        solar_radiation_w_m2=520.0,
        root_zone_moisture_pct=34.0,
        ec=1.4,
        ph=6.1,
        vent_open_pct=10.0,
        weather=WeatherForecast(rain_probability=70.0, expected_rain_mm=6.0),
        image=ImageGrowthSignals(
            ripe_fruit_ratio=0.82,
            average_fruit_size_mm=31.0,
            fruit_count=45,
        ),
    )

    engine = BerryNextDecisionEngine()
    for item in engine.recommend(snapshot):
        print(f"[{item.priority}] {item.action} score={item.score}")
        print(f"  reason: {item.reason}")
        if item.safeguards:
            print(f"  safeguards: {', '.join(item.safeguards)}")


if __name__ == "__main__":
    main()
