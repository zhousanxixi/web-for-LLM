import csv
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from io import StringIO

from util.http_get import fetch_json, fetch_text

WEATHER_URL = (
    "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"
    "?dataType=rhrread&lang=tc"
)
WARNING_URL = (
    "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"
    "?dataType=warnsum&lang=tc"
)
RSS_URL = "https://rss.weather.gov.hk/rss/CurrentWeather.xml"
TEMPERATURE_CSV_URL = (
    "https://data.weather.gov.hk/weatherAPI/hko_data/"
    "regional-weather/latest_1min_temperature.csv"
)
HISTORICAL_MAX_URL = (
    "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php"
    "?dataType=CLMMAXT&rformat=csv&station={station}"
)
HEAT_INDEX_CSV_URL = (
    "https://data.weather.gov.hk/weatherAPI/hko_data/"
    "regional-weather/recent10_10min_hkhi_sc.csv"
)
WIND_CSV_URL = (
    "https://data.weather.gov.hk/weatherAPI/hko_data/"
    "regional-weather/latest_10min_wind.csv"
)
VISIBILITY_CSV_URL = (
    "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php"
    "?dataType=LTMV&lang=en&rformat=csv"
)
HUMIDITY_CSV_URL = (
    "https://data.weather.gov.hk/weatherAPI/hko_data/"
    "regional-weather/latest_1min_humidity.csv"
)
UV_INDEX_CSV_URL = (
    "https://data.weather.gov.hk/weatherAPI/hko_data/"
    "regional-weather/latest_15min_uvindex.csv"
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def rss_bulletin(xml_text: str) -> tuple[str, list[str]]:
    root = ET.fromstring(xml_text)
    item = root.find("channel/item")
    title = (item.findtext("title") or "").strip() if item is not None else ""
    description = item.findtext("description") or "" if item is not None else ""

    extractor = _TextExtractor()
    extractor.feed(description)
    lines = [
        line
        for line in extractor.parts
        if line.startswith("Air temperature") or line.startswith("Relative Humidity")
    ]
    return title, lines


def hko_temperature(weather: dict) -> str:
    for item in weather.get("temperature", {}).get("data", []):
        if item.get("place") == "香港天文台":
            return f"{item['value']}°{item['unit']}"
    return "没有找到香港天文台气温"


def latest_temperatures(csv_text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(csv_text)))


def latest_humidity(csv_text: str) -> list[dict[str, str]]:
    rows = []
    for row in csv.DictReader(StringIO(csv_text.lstrip("\ufeff"))):
        rows.append({key.lstrip("\ufeff"): value for key, value in row.items() if key})
    return rows


def latest_visibility(csv_text: str) -> list[dict[str, str]]:
    rows = []
    for row in csv.DictReader(StringIO(csv_text.lstrip("\ufeff"))):
        rows.append({key.lstrip("\ufeff"): value for key, value in row.items() if key})
    return rows


def latest_uv_index(csv_text: str) -> dict[str, str] | None:
    rows = []
    for row in csv.DictReader(StringIO(csv_text.lstrip("\ufeff"))):
        rows.append({key.lstrip("\ufeff"): value for key, value in row.items() if key})
    return rows[-1] if rows else None


def latest_winds(csv_text: str) -> list[dict[str, str]]:
    rows = []
    for row in csv.DictReader(StringIO(csv_text.lstrip("\ufeff"))):
        rows.append({key.lstrip("\ufeff"): value for key, value in row.items() if key})
    return rows


def heat_index_readings(csv_text: str) -> list[dict[str, str]]:
    rows = []
    for row in csv.DictReader(StringIO(csv_text.lstrip("\ufeff"))):
        rows.append({key.lstrip("\ufeff"): value for key, value in row.items() if key})
    return rows


def daily_maximum_temperatures(csv_text: str) -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    for line in csv_text.splitlines():
        line = line.strip().lstrip("\ufeff")
        if not line or not line[0].isdigit():
            continue
        parts = next(csv.reader([line]))
        if len(parts) < 4:
            continue
        try:
            temperature = float(parts[3])
        except ValueError:
            continue
        rows.append(
            {
                "year": parts[0],
                "month": parts[1],
                "day": parts[2],
                "temperature": temperature,
                "completeness": parts[4] if len(parts) > 4 else "",
            }
        )
    return rows


def active_warnings(warnings: dict) -> list[str]:
    lines = []
    for item in warnings.values():
        if isinstance(item, dict) and item.get("name"):
            lines.append(f"{item['name']}（{item.get('code', '')}）")
    return lines


def main() -> None:
    weather = fetch_json(WEATHER_URL)
    warnings = fetch_json(WARNING_URL)
    title, bulletin_lines = rss_bulletin(fetch_text(RSS_URL))
    temperatures = latest_temperatures(fetch_text(TEMPERATURE_CSV_URL))

    print(f"更新时间: {weather.get('updateTime', '未知')}")
    print(f"香港天文台气温: {hko_temperature(weather)}")

    warning_lines = active_warnings(warnings)
    if warning_lines:
        print("正在生效的警告:")
        for line in warning_lines:
            print(f"- {line}")
    else:
        print("正在生效的警告: 无")

    print(f"RSS 公报: {title}")
    for line in bulletin_lines:
        print(f"- {line}")

    if temperatures:
        print(f"最新一分钟平均气温: {temperatures[0]['Date time']}")
        for row in temperatures:
            station = row["Automatic Weather Station"]
            value = row["Air Temperature(degree Celsius)"]
            print(f"- {station}: {value}°C")
    else:
        print("最新一分钟平均气温: 无数据")

    heat_rows = heat_index_readings(fetch_text(HEAT_INDEX_CSV_URL))
    if heat_rows:
        latest = heat_rows[-1]["日期时间"]
        print(f"最新十分钟平均香港暑热指数: {latest}")
        for row in heat_rows:
            if row["日期时间"] == latest:
                print(f"- {row['自动气象站']}: {row['十分钟平均香港暑热指数']}")
    else:
        print("香港暑热指数: 无数据")

    winds = latest_winds(fetch_text(WIND_CSV_URL))
    if winds:
        print(f"最新十分钟平均风: {winds[0]['Date time']}")
        for row in winds:
            print(
                f"- {row['Automatic Weather Station']}: "
                f"{row['10-Minute Mean Wind Direction(Compass points)']} "
                f"{row['10-Minute Mean Speed(km/hour)']} km/h, "
                f"gust {row['10-Minute Maximum Gust(km/hour)']} km/h"
            )
    else:
        print("最新十分钟平均风: 无数据")

    visibility = latest_visibility(fetch_text(VISIBILITY_CSV_URL))
    if visibility:
        print(f"最新十分钟平均能见度: {visibility[0]['Date time']}")
        for row in visibility:
            print(f"- {row['Automatic Weather Station']}: {row['10 minute mean visibility']}")
    else:
        print("最新十分钟平均能见度: 无数据")

    humidity = latest_humidity(fetch_text(HUMIDITY_CSV_URL))
    if humidity:
        print(f"最新一分钟平均相对湿度: {humidity[0]['Date time']}")
        for row in humidity:
            print(f"- {row['Automatic Weather Station']}: {row['Relative Humidity(percent)']}%")
    else:
        print("最新一分钟平均相对湿度: 无数据")

    uv = latest_uv_index(fetch_text(UV_INDEX_CSV_URL))
    if uv:
        print(f"最新十五分钟平均紫外线指数: {uv['Date time']} {uv['past 15-minute mean UV Index']}")
    else:
        print("最新十五分钟平均紫外线指数: 无数据")


if __name__ == "__main__":
    main()
