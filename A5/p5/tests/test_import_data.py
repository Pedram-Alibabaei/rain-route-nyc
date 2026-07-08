from datetime import datetime
from pathlib import Path
import sys

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))

from import_data import clean_and_enrich, time_band, weather_condition


def test_weather_condition_prefers_measured_precipitation():
    assert weather_condition(0, 1.2, 0) == "rain"
    assert weather_condition(0, 0, 0.5) == "snow"
    assert weather_condition(0, 0, 0) == "dry"
    assert weather_condition(None, 0, 0) == "unknown"
    assert weather_condition(999, 0, 0) == "other"


def test_time_band_boundaries():
    assert time_band(4) == "night"
    assert time_band(5) == "morning"
    assert time_band(10) == "day"
    assert time_band(16) == "evening"
    assert time_band(21) == "night"


def test_clean_and_enrich_filters_invalid_rows_and_joins_weather():
    trips = pl.DataFrame(
        [
            {
                "tpep_pickup_datetime": datetime(2025, 1, 15, 8, 15),
                "tpep_dropoff_datetime": datetime(2025, 1, 15, 8, 35),
                "passenger_count": 1,
                "trip_distance": 2.5,
                "PULocationID": 161,
                "DOLocationID": 236,
                "payment_type": 1,
                "fare_amount": 18.5,
                "tip_amount": 3.5,
                "total_amount": 25.0,
            },
            {
                "tpep_pickup_datetime": datetime(2025, 1, 15, 9, 0),
                "tpep_dropoff_datetime": datetime(2025, 1, 15, 9, 0),
                "passenger_count": 1,
                "trip_distance": 1.0,
                "PULocationID": 161,
                "DOLocationID": 236,
                "payment_type": 1,
                "fare_amount": 8.0,
                "tip_amount": 1.0,
                "total_amount": 11.0,
            },
            {
                "tpep_pickup_datetime": datetime(2025, 2, 1, 0, 5),
                "tpep_dropoff_datetime": datetime(2025, 2, 1, 0, 25),
                "passenger_count": 1,
                "trip_distance": 3.0,
                "PULocationID": 161,
                "DOLocationID": 236,
                "payment_type": 1,
                "fare_amount": 20.0,
                "tip_amount": 4.0,
                "total_amount": 28.0,
            },
        ]
    )
    weather = pl.DataFrame(
        [
            {
                "timestamp": datetime(2025, 1, 15, 8),
                "temperature_c": 3.2,
                "humidity_pct": 80,
                "precipitation_mm": 1.1,
                "rain_mm": 1.1,
                "snowfall_cm": 0.0,
                "wind_speed_kmh": 12.0,
                "weather_code": 61,
                "condition": "rain",
            }
        ]
    )

    cleaned = clean_and_enrich(trips, weather, 2025, 1)

    assert cleaned.height == 1
    row = cleaned.to_dicts()[0]
    assert row["duration_minutes"] == 20.0
    assert row["pickup_hour"] == datetime(2025, 1, 15, 8)
    assert row["time_band"] == "morning"
    assert row["condition"] == "rain"
    assert row["temperature_c"] == 3.2
