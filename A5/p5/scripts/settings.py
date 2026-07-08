from pathlib import Path
import os

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

load_dotenv(ROOT / ".env")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27018")
MONGO_DB = os.getenv("MONGO_DB", "taxi_weather")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7689")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "taxiweatherpass")

NYC_LATITUDE = 40.7128
NYC_LONGITUDE = -74.0060
NYC_TIMEZONE = "America/New_York"


def month_key(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def raw_month_dir(year: int, month: int) -> Path:
    path = RAW_DIR / month_key(year, month)
    path.mkdir(parents=True, exist_ok=True)
    return path


def processed_month_dir(year: int, month: int) -> Path:
    path = PROCESSED_DIR / month_key(year, month)
    path.mkdir(parents=True, exist_ok=True)
    return path
