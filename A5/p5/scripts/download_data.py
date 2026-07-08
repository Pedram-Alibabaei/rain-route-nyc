import argparse
import calendar
from pathlib import Path

import requests

from settings import NYC_LATITUDE, NYC_LONGITUDE, NYC_TIMEZONE, raw_month_dir


TLC_BASE_URL = "https://d37ci6vzurychx.cloudfront.net"
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"


def download_file(url: str, target: Path) -> None:
    if target.exists() and target.stat().st_size > 0:
        print(f"exists: {target}")
        return

    print(f"download: {url}")
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    print(f"saved: {target} ({target.stat().st_size / 1024 / 1024:.1f} MB)")


def download_weather(year: int, month: int, target: Path) -> None:
    if target.exists() and target.stat().st_size > 0:
        print(f"exists: {target}")
        return

    last_day = calendar.monthrange(year, month)[1]
    params = {
        "latitude": NYC_LATITUDE,
        "longitude": NYC_LONGITUDE,
        "start_date": f"{year}-{month:02d}-01",
        "end_date": f"{year}-{month:02d}-{last_day:02d}",
        "timezone": NYC_TIMEZONE,
        "hourly": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation",
                "rain",
                "snowfall",
                "wind_speed_10m",
                "weather_code",
            ]
        ),
    }

    print("download: Open-Meteo hourly weather")
    response = requests.get(OPEN_METEO_URL, params=params, timeout=60)
    response.raise_for_status()
    target.write_text(response.text, encoding="utf-8")
    print(f"saved: {target}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download NYC taxi, zone lookup, and weather data.")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--month", type=int, default=1)
    args = parser.parse_args()

    out_dir = raw_month_dir(args.year, args.month)
    trip_file = out_dir / f"yellow_tripdata_{args.year}-{args.month:02d}.parquet"
    zone_file = out_dir / "taxi_zone_lookup.csv"
    weather_file = out_dir / "weather_hourly.json"

    download_file(
        f"{TLC_BASE_URL}/trip-data/yellow_tripdata_{args.year}-{args.month:02d}.parquet",
        trip_file,
    )
    download_file(f"{TLC_BASE_URL}/misc/taxi_zone_lookup.csv", zone_file)
    download_weather(args.year, args.month, weather_file)


if __name__ == "__main__":
    main()
