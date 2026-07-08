import argparse
import json
from datetime import datetime, timezone

import pandas as pd
import polars as pl
from neo4j import GraphDatabase
from pymongo import MongoClient, ReplaceOne

from settings import (
    MONGO_DB,
    MONGO_URI,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    processed_month_dir,
    raw_month_dir,
)


WEATHER_CODE_GROUPS = {
    "dry": {0, 1, 2, 3, 45, 48},
    "rain": {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99},
    "snow": {71, 73, 75, 77, 85, 86},
}


def weather_condition(code: int | None, precipitation: float | None, snowfall: float | None) -> str:
    if snowfall and snowfall > 0:
        return "snow"
    if precipitation and precipitation > 0:
        return "rain"
    if code is None:
        return "unknown"
    for condition, codes in WEATHER_CODE_GROUPS.items():
        if int(code) in codes:
            return condition
    return "other"


def time_band(hour: int) -> str:
    if 5 <= hour < 10:
        return "morning"
    if 10 <= hour < 16:
        return "day"
    if 16 <= hour < 21:
        return "evening"
    return "night"


def read_weather(raw_dir):
    payload = json.loads((raw_dir / "weather_hourly.json").read_text(encoding="utf-8"))
    hourly = payload["hourly"]
    rows = []
    for idx, timestamp in enumerate(hourly["time"]):
        precipitation = hourly.get("precipitation", [None])[idx]
        snowfall = hourly.get("snowfall", [None])[idx]
        code = hourly.get("weather_code", [None])[idx]
        rows.append(
            {
                "timestamp": timestamp,
                "temperature_c": hourly.get("temperature_2m", [None])[idx],
                "humidity_pct": hourly.get("relative_humidity_2m", [None])[idx],
                "precipitation_mm": precipitation,
                "rain_mm": hourly.get("rain", [None])[idx],
                "snowfall_cm": snowfall,
                "wind_speed_kmh": hourly.get("wind_speed_10m", [None])[idx],
                "weather_code": code,
                "condition": weather_condition(code, precipitation, snowfall),
            }
        )
    return pl.DataFrame(rows).with_columns(
        pl.col("timestamp").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M")
    )


def load_trips(raw_dir, limit: int | None):
    trip_files = list(raw_dir.glob("yellow_tripdata_*.parquet"))
    if not trip_files:
        raise FileNotFoundError(f"No yellow_tripdata parquet found in {raw_dir}")

    columns = [
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
        "passenger_count",
        "trip_distance",
        "PULocationID",
        "DOLocationID",
        "payment_type",
        "fare_amount",
        "tip_amount",
        "total_amount",
    ]

    lazy = pl.scan_parquet(trip_files[0]).select(columns)
    if limit:
        lazy = lazy.head(limit)
    return lazy.collect()


def clean_and_enrich(trips: pl.DataFrame, weather: pl.DataFrame, year: int, month: int) -> pl.DataFrame:
    month_start = datetime(year, month, 1)
    if month == 12:
        month_end = datetime(year + 1, 1, 1)
    else:
        month_end = datetime(year, month + 1, 1)

    weather_join = weather.rename({"timestamp": "pickup_hour"})

    return (
        trips.with_columns(
            [
                ((pl.col("tpep_dropoff_datetime") - pl.col("tpep_pickup_datetime")).dt.total_seconds() / 60)
                .round(2)
                .alias("duration_minutes"),
                pl.col("tpep_pickup_datetime").dt.truncate("1h").alias("pickup_hour"),
                pl.col("tpep_pickup_datetime").dt.hour().map_elements(time_band, return_dtype=pl.String).alias("time_band"),
            ]
        )
        .filter(pl.col("tpep_pickup_datetime").is_between(month_start, month_end, closed="left"))
        .filter(pl.col("duration_minutes").is_between(1, 180))
        .filter(pl.col("trip_distance").is_between(0.1, 80))
        .filter(pl.col("fare_amount") >= 0)
        .filter(pl.col("total_amount") >= 0)
        .filter(pl.col("PULocationID").is_not_null() & pl.col("DOLocationID").is_not_null())
        .join(weather_join, on="pickup_hour", how="left")
        .with_row_index("trip_id")
    )


def import_mongo(df: pl.DataFrame, weather: pl.DataFrame, zones: pd.DataFrame, month_label: str) -> None:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]

    db.trips.delete_many({"month": month_label})
    db.weather_hourly.delete_many({"month": month_label})
    db.zones.delete_many({})

    weather_docs = [
        {**row, "month": month_label, "timestamp": row["timestamp"].isoformat()}
        for row in weather.to_dicts()
    ]
    if weather_docs:
        db.weather_hourly.insert_many(weather_docs)

    zone_docs = [
        {
            "location_id": int(row.LocationID),
            "borough": row.Borough,
            "zone": row.Zone,
            "service_zone": row.service_zone,
        }
        for row in zones.itertuples(index=False)
    ]
    db.zones.insert_many(zone_docs)

    columns = {
        "trip_id": "trip_id",
        "tpep_pickup_datetime": "pickup_at",
        "tpep_dropoff_datetime": "dropoff_at",
        "pickup_hour": "pickup_hour",
        "PULocationID": "pickup_zone_id",
        "DOLocationID": "dropoff_zone_id",
        "passenger_count": "passenger_count",
        "trip_distance": "distance_miles",
        "duration_minutes": "duration_minutes",
        "payment_type": "payment_type",
        "fare_amount": "fare_amount",
        "tip_amount": "tip_amount",
        "total_amount": "total_amount",
        "time_band": "time_band",
        "temperature_c": "temperature_c",
        "precipitation_mm": "precipitation_mm",
        "snowfall_cm": "snowfall_cm",
        "wind_speed_kmh": "wind_speed_kmh",
        "condition": "weather_condition",
    }
    trip_docs = []
    for row in df.select(list(columns.keys())).to_dicts():
        doc = {target: value for source, target in columns.items() for value in [row[source]]}
        doc["_id"] = f"{month_label}-{doc['trip_id']}"
        doc["month"] = month_label
        for key in ("pickup_at", "dropoff_at", "pickup_hour"):
            if doc.get(key):
                doc[key] = doc[key].isoformat()
        trip_docs.append(doc)

    batch_size = 5000
    for start in range(0, len(trip_docs), batch_size):
        batch = trip_docs[start : start + batch_size]
        db.trips.bulk_write([ReplaceOne({"_id": doc["_id"]}, doc, upsert=True) for doc in batch])
        print(f"MongoDB trips: {min(start + batch_size, len(trip_docs))}/{len(trip_docs)}")

    db.trips.create_index([("month", 1), ("pickup_at", 1)])
    db.trips.create_index([("pickup_zone_id", 1), ("dropoff_zone_id", 1)])
    db.trips.create_index([("weather_condition", 1), ("time_band", 1)])
    db.weather_hourly.create_index([("month", 1), ("timestamp", 1)], unique=True)
    db.zones.create_index("location_id", unique=True)


def import_neo4j(df: pl.DataFrame, zones: pd.DataFrame, month_label: str) -> None:
    route_stats = (
        df.group_by(["PULocationID", "DOLocationID", "condition", "time_band"])
        .agg(
            [
                pl.len().alias("trip_count"),
                pl.col("duration_minutes").mean().round(2).alias("avg_duration_minutes"),
                pl.col("fare_amount").mean().round(2).alias("avg_fare_amount"),
                pl.col("tip_amount").mean().round(2).alias("avg_tip_amount"),
                pl.col("trip_distance").mean().round(2).alias("avg_distance_miles"),
            ]
        )
        .filter(pl.col("trip_count") >= 3)
    )

    zone_rows = [
        {
            "id": int(row.LocationID),
            "name": row.Zone,
            "borough": row.Borough,
            "service_zone": row.service_zone,
        }
        for row in zones.itertuples(index=False)
    ]
    route_rows = [
        {
            "start_id": int(row["PULocationID"]),
            "end_id": int(row["DOLocationID"]),
            "month": month_label,
            "weather": row["condition"] or "unknown",
            "time_band": row["time_band"],
            "trip_count": int(row["trip_count"]),
            "avg_duration_minutes": float(row["avg_duration_minutes"]),
            "avg_fare_amount": float(row["avg_fare_amount"]),
            "avg_tip_amount": float(row["avg_tip_amount"]),
            "avg_distance_miles": float(row["avg_distance_miles"]),
        }
        for row in route_stats.to_dicts()
    ]

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        session.run("MATCH ()-[r:TRIPS_TO {month: $month}]->() DELETE r", month=month_label)
        session.run("CREATE CONSTRAINT zone_id IF NOT EXISTS FOR (z:Zone) REQUIRE z.id IS UNIQUE")
        session.run(
            """
            UNWIND $zones AS zone
            MERGE (z:Zone {id: zone.id})
            SET z.name = zone.name,
                z.borough = zone.borough,
                z.service_zone = zone.service_zone
            """,
            zones=zone_rows,
        )
        for start in range(0, len(route_rows), 1000):
            batch = route_rows[start : start + 1000]
            session.run(
                """
                UNWIND $routes AS route
                MATCH (a:Zone {id: route.start_id})
                MATCH (b:Zone {id: route.end_id})
                MERGE (a)-[r:TRIPS_TO {
                    month: route.month,
                    weather: route.weather,
                    time_band: route.time_band
                }]->(b)
                SET r.trip_count = route.trip_count,
                    r.avg_duration_minutes = route.avg_duration_minutes,
                    r.avg_fare_amount = route.avg_fare_amount,
                    r.avg_tip_amount = route.avg_tip_amount,
                    r.avg_distance_miles = route.avg_distance_miles
                """,
                routes=batch,
            )
            print(f"Neo4j routes: {min(start + 1000, len(route_rows))}/{len(route_rows)}")
    driver.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean NYC taxi data and import into MongoDB and Neo4j.")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--month", type=int, default=1)
    parser.add_argument("--limit", type=int, default=200000, help="0 imports the full month.")
    parser.add_argument("--dry-run", action="store_true", help="Only clean and write processed parquet; skip databases.")
    args = parser.parse_args()

    month_label = f"{args.year}-{args.month:02d}"
    raw_dir = raw_month_dir(args.year, args.month)
    processed_dir = processed_month_dir(args.year, args.month)

    limit = None if args.limit == 0 else args.limit
    weather = read_weather(raw_dir)
    trips = load_trips(raw_dir, limit)
    cleaned = clean_and_enrich(trips, weather, args.year, args.month)
    zones = pd.read_csv(raw_dir / "taxi_zone_lookup.csv")

    processed_file = processed_dir / "trips_cleaned.parquet"
    cleaned.write_parquet(processed_file)
    print(f"processed: {processed_file} ({len(cleaned):,} rows)")

    if args.dry_run:
        print("dry run: skipped MongoDB and Neo4j import")
        return

    import_mongo(cleaned, weather, zones, month_label)
    import_neo4j(cleaned, zones, month_label)
    print("done")


if __name__ == "__main__":
    main()
