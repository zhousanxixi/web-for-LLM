import csv
import math
import sys
from pathlib import Path

STATION_INFO_DIR = Path(__file__).resolve().parent.parent / "station_info"
STATIONS_PATH = STATION_INFO_DIR / "temperature_station.csv"
HEAT_INDEX_STATIONS_PATH = STATION_INFO_DIR / "heat_index_station.csv"
WIND_STATIONS_PATH = STATION_INFO_DIR / "wind_station.csv"
VISIBILITY_STATIONS_PATH = STATION_INFO_DIR / "visibility_station.csv"
HUMIDITY_STATIONS_PATH = STATION_INFO_DIR / "humidity_station.csv"


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(a))


def load_stations(path: Path = STATIONS_PATH) -> list[dict[str, float | str]]:
    with path.open(newline="") as f:
        rows = []
        for row in csv.DictReader(f):
            rows.append(
                {
                    "name": row["name"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                }
            )
    return rows


def nearest_station(
    latitude: float,
    longitude: float,
    stations: list[dict[str, float | str]] | None = None,
) -> dict[str, float | str]:
    stations = load_stations() if stations is None else stations
    if not stations:
        raise ValueError("没有可比较的气象站")
    closest = min(
        stations,
        key=lambda station: distance_km(
            latitude,
            longitude,
            float(station["latitude"]),
            float(station["longitude"]),
        ),
    )
    distance = distance_km(
        latitude,
        longitude,
        float(closest["latitude"]),
        float(closest["longitude"]),
    )
    return {
        "name": closest["name"],
        "latitude": closest["latitude"],
        "longitude": closest["longitude"],
        "distance_km": distance,
    }


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("用法: python nearest_station.py 22.305040 114.189521")
    result = nearest_station(float(sys.argv[1]), float(sys.argv[2]))
    print(result["name"])
    print(f"约 {float(result['distance_km']):.1f} 公里")


if __name__ == "__main__":
    main()
