import sys
from pathlib import Path
from urllib.error import URLError

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp.server import MCPServer

from util.geocode import geocode_place
from util.nearest_station import (
    HEAT_INDEX_STATIONS_PATH,
    HUMIDITY_STATIONS_PATH,
    VISIBILITY_STATIONS_PATH,
    WIND_STATIONS_PATH,
    load_stations,
    nearest_station,
)
from queries.fetch_weather import (
    HISTORICAL_MAX_URL,
    TEMPERATURE_CSV_URL,
    active_warnings,
    daily_maximum_temperatures,
    fetch_json,
    fetch_text,
    hko_temperature,
    HEAT_INDEX_CSV_URL,
    HUMIDITY_CSV_URL,
    UV_INDEX_CSV_URL,
    VISIBILITY_CSV_URL,
    WIND_CSV_URL,
    heat_index_readings,
    latest_humidity,
    latest_temperatures,
    latest_uv_index,
    latest_visibility,
    latest_winds,
)

mcp = MCPServer(
    "Hong Kong Weather",
    instructions=(
        "提供香港天文台的实时天气。"
        "问现在多少度、某个地名附近的气温、天气预报、九天预报、有没有生效警告、"
        "警告的官方说明、特别天气提示、暑热指数、风速风向、能见度、相对湿度、紫外线指数，或往年最高日气温时，调用对应工具。"
        "没有指定地点的相对湿度用 get_humidity。"
        "用户给出地区、车站或地标并询问相对湿度时，用 get_nearest_humidity。"
        "没有指定地点的能见度用 get_visibility。"
        "用户给出地区、车站或地标并询问能见度时，用 get_nearest_visibility。"
        "紫外线指数是全港一个数值，用 get_uv_index，不能按地名选择。"
        "香港暑热指数用 get_heat_index。"
        "用户给出的是地区、车站或地标，并询问暑热指数时，用 get_nearest_heat_index。"
        "没有指定地点的风速或风向用 get_wind。"
        "用户给出地区、车站或地标并询问风速或风向时，用 get_nearest_wind。"
        "地名不是气象站英文名时，用 get_nearest_temperature。"
        "天文台当前气温用 get_weather_info 的 current。"
        "正在生效的警告用 get_weather_info 的 warnings。"
        "本港预报、九天预报、详细警告和特别提示也用 get_weather_info。"
    ),
)


def _failed(exc: Exception) -> str:
    return f"获取天文台数据失败: {exc}"


@mcp.tool()
def get_station_temperatures(station: str = "") -> str:
    """返回香港各自动气象站最新一分钟平均气温。

    station 可填英文站名的一部分，例如 Observatory 或 Sha Tin。
    留空则返回全部站点。
    """
    try:
        rows = latest_temperatures(fetch_text(TEMPERATURE_CSV_URL))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _failed(exc)
    if not rows:
        return "最新一分钟平均气温: 无数据"

    query = station.strip().lower()
    if query:
        rows = [
            row
            for row in rows
            if query in row["Automatic Weather Station"].lower()
        ]
        if not rows:
            return f"没有找到名称包含 {station!r} 的气象站。"

    observed_at = rows[0]["Date time"]
    lines = [
        f"- {row['Automatic Weather Station']}: {row['Air Temperature(degree Celsius)']}°C"
        for row in rows
    ]
    return f"最新一分钟平均气温: {observed_at}\n" + "\n".join(lines)


@mcp.tool()
def get_nearest_temperature(place: str) -> str:
    """根据香港地名查找最近气象站的最新一分钟平均气温。

    place 是地区、车站或地标，例如黄埔、沙田、香港理工大学。
    返回匹配到的地点、最近气象站、距离和该站气温。
    """
    located = geocode_place(place)
    if located is None:
        return f"没有找到地名 {place}。"
    station = nearest_station(
        float(located["latitude"]),
        float(located["longitude"]),
    )
    try:
        rows = latest_temperatures(fetch_text(TEMPERATURE_CSV_URL))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _failed(exc)
    matched = [
        row
        for row in rows
        if row["Automatic Weather Station"] == station["name"]
    ]
    if not matched:
        return f"找到最近气象站 {station['name']}，但当前气温数据里没有该站。"
    row = matched[0]
    return (
        f"查询地名: {place}\n"
        f"匹配地点: {located['name']}\n"
        f"最近气象站: {station['name']}\n"
        f"距离: 约 {float(station['distance_km']):.1f} 公里\n"
        f"最新一分钟平均气温: {row['Date time']}\n"
        f"{station['name']}: {row['Air Temperature(degree Celsius)']}°C"
    )


@mcp.tool()
def get_historical_max_temperature(station: str = "CCH", year: int = 0) -> str:
    """返回某气象站往年的最高日气温，以及出现的日期。

    station 是天文台站号，默认 CCH（长洲）。天文台总部用 HKO。
    year 为四位年份时只统计该年；0 表示在全部历史记录中找最高值。
    """
    code = station.strip().upper()
    if not code.isalnum():
        return "站号只能包含字母和数字，例如 CCH 或 HKO。"
    try:
        csv_text = fetch_text(HISTORICAL_MAX_URL.format(station=code), timeout=60)
        rows = daily_maximum_temperatures(csv_text)
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _failed(exc)
    if year:
        rows = [row for row in rows if int(str(row["year"])) == year]
    if not rows:
        scope = f"{year}年" if year else "全部年份"
        return f"站点 {code} 在{scope}没有可用的日最高气温。"

    highest = max(float(row["temperature"]) for row in rows)
    matches = [row for row in rows if float(row["temperature"]) == highest]
    scope = f"{year}年" if year else "全部历史记录"
    lines = []
    for row in matches[:10]:
        completeness = "数据完整" if row["completeness"] == "C" else "数据不完整"
        lines.append(
            f"- {row['year']}-{int(row['month']):02d}-{int(row['day']):02d}"
            f"（{completeness}）"
        )
    extra = ""
    if len(matches) > 10:
        extra = f"\n另有 {len(matches) - 10} 天相同，未全部列出。"
    return (
        f"站点: {code}\n"
        f"统计范围: {scope}\n"
        f"最高日气温: {highest}°C\n"
        "出现日期:\n" + "\n".join(lines) + extra
    )


@mcp.tool()
def get_heat_index(station: str = "") -> str:
    """返回最近的十分钟平均香港暑热指数。此为临时数据。

    文件含最近十组读数，站名与文件一致，例如天文台、沙田、京士柏、跑馬地。
    station 留空时返回最新一组各站指数。
    填写站名的一部分时，返回该站最近十组。
    """
    try:
        rows = heat_index_readings(fetch_text(HEAT_INDEX_CSV_URL))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _failed(exc)
    if not rows:
        return "香港暑热指数: 无数据"

    query = station.strip()
    if query:
        matched = [row for row in rows if query in row["自动气象站"]]
        if not matched:
            names = []
            for row in rows:
                name = row["自动气象站"]
                if name not in names:
                    names.append(name)
            return f"没有找到名称包含 {station!r} 的气象站。现有站点: {'、'.join(names)}"
        lines = [
            f"- {row['日期时间']} {row['自动气象站']}: {row['十分钟平均香港暑热指数']}"
            for row in matched
        ]
        return "最近十组十分钟平均香港暑热指数（临时数据）:\n" + "\n".join(lines)

    latest = rows[-1]["日期时间"]
    lines = [
        f"- {row['自动气象站']}: {row['十分钟平均香港暑热指数']}"
        for row in rows
        if row["日期时间"] == latest
    ]
    return f"最新十分钟平均香港暑热指数（临时数据）: {latest}\n" + "\n".join(lines)


@mcp.tool()
def get_nearest_heat_index(place: str) -> str:
    """根据香港地名查找最近暑热指数站的十分钟平均香港暑热指数。

    place 是地区、车站或地标，例如黄埔、沙田、香港理工大学。
    只在提供暑热指数的气象站中找最近的一个。
    返回匹配地点、最近暑热指数站、距离，以及该站最新读数。
    """
    located = geocode_place(place)
    if located is None:
        return f"没有找到地名 {place}。"
    station = nearest_station(
        float(located["latitude"]),
        float(located["longitude"]),
        load_stations(HEAT_INDEX_STATIONS_PATH),
    )
    try:
        rows = heat_index_readings(fetch_text(HEAT_INDEX_CSV_URL))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _failed(exc)
    matched = [row for row in rows if row["自动气象站"] == station["name"]]
    if not matched:
        return f"找到最近暑热指数站 {station['name']}，但当前数据里没有该站。"
    latest = matched[-1]
    return (
        f"查询地名: {place}\n"
        f"匹配地点: {located['name']}\n"
        f"最近暑热指数站: {station['name']}\n"
        f"距离: 约 {float(station['distance_km']):.1f} 公里\n"
        f"最新十分钟平均香港暑热指数（临时数据）: {latest['日期时间']}\n"
        f"{station['name']}: {latest['十分钟平均香港暑热指数']}"
    )


WIND_DIRECTIONS = {
    "north": "北",
    "northeast": "东北",
    "east": "东",
    "southeast": "东南",
    "south": "南",
    "southwest": "西南",
    "west": "西",
    "northwest": "西北",
    "variable": "风向不定",
    "calm": "无风",
}


def _wind_line(row: dict[str, str]) -> str:
    direction = row["10-Minute Mean Wind Direction(Compass points)"]
    label = WIND_DIRECTIONS.get(direction.strip().lower(), direction)
    return (
        f"- {row['Automatic Weather Station']}: {label}，"
        f"平均风速 {row['10-Minute Mean Speed(km/hour)']} 公里/小时，"
        f"最高阵风 {row['10-Minute Maximum Gust(km/hour)']} 公里/小时"
    )


@mcp.tool()
def get_wind(station: str = "") -> str:
    """返回各气象站最新十分钟平均风向、平均风速和最高阵风。

    station 可填英文站名的一部分，例如 Cheung Chau 或 Kai Tak。
    留空则返回全部站点。
    """
    try:
        rows = latest_winds(fetch_text(WIND_CSV_URL))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _failed(exc)
    if not rows:
        return "最新十分钟平均风: 无数据"

    query = station.strip().lower()
    if query:
        rows = [
            row
            for row in rows
            if query in row["Automatic Weather Station"].lower()
        ]
        if not rows:
            return f"没有找到名称包含 {station!r} 的风速站。"

    observed_at = rows[0]["Date time"]
    return f"最新十分钟平均风: {observed_at}\n" + "\n".join(_wind_line(row) for row in rows)


@mcp.tool()
def get_nearest_wind(place: str) -> str:
    """根据香港地名查找最近风速站的十分钟平均风向、平均风速和最高阵风。

    place 是地区、车站或地标，例如黄埔、长洲、赤柱。
    只在提供风速的气象站中找最近的一个。
    """
    located = geocode_place(place)
    if located is None:
        return f"没有找到地名 {place}。"
    station = nearest_station(
        float(located["latitude"]),
        float(located["longitude"]),
        load_stations(WIND_STATIONS_PATH),
    )
    try:
        rows = latest_winds(fetch_text(WIND_CSV_URL))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _failed(exc)
    matched = [
        row
        for row in rows
        if row["Automatic Weather Station"] == station["name"]
    ]
    if not matched:
        return f"找到最近风速站 {station['name']}，但当前风速数据里没有该站。"
    row = matched[0]
    return (
        f"查询地名: {place}\n"
        f"匹配地点: {located['name']}\n"
        f"最近风速站: {station['name']}\n"
        f"距离: 约 {float(station['distance_km']):.1f} 公里\n"
        f"最新十分钟平均风: {row['Date time']}\n"
        + _wind_line(row)
    )


def _visibility_text(raw: str) -> str:
    text = raw.strip()
    if text.lower().endswith("km"):
        return text[:-2].strip() + " 公里"
    if text.lower().endswith("m"):
        return text[:-1].strip() + " 米"
    return text


def _visibility_line(row: dict[str, str]) -> str:
    return (
        f"- {row['Automatic Weather Station']}: "
        f"{_visibility_text(row['10 minute mean visibility'])}"
    )


@mcp.tool()
def get_visibility(station: str = "") -> str:
    """返回中环、赤鱲角、西湾河和横澜岛的最新十分钟平均能见度。

    station 可填英文站名的一部分，例如 Central 或 Waglan。
    留空则返回全部四个站点。
    """
    try:
        rows = latest_visibility(fetch_text(VISIBILITY_CSV_URL))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _failed(exc)
    if not rows:
        return "最新十分钟平均能见度: 无数据"

    query = station.strip().lower()
    if query:
        rows = [
            row
            for row in rows
            if query in row["Automatic Weather Station"].lower()
        ]
        if not rows:
            return f"没有找到名称包含 {station!r} 的能见度站。现有站点: Central、Chek Lap Kok、Sai Wan Ho、Waglan Island。"

    observed_at = rows[0]["Date time"]
    return f"最新十分钟平均能见度: {observed_at}\n" + "\n".join(
        _visibility_line(row) for row in rows
    )


@mcp.tool()
def get_nearest_visibility(place: str) -> str:
    """根据香港地名查找最近能见度站的十分钟平均能见度。

    place 是地区、车站或地标，例如黄埔、赤柱、机场。
    只在 Central、Chek Lap Kok、Sai Wan Ho、Waglan Island 四个站中找最近的一个。
    """
    located = geocode_place(place)
    if located is None:
        return f"没有找到地名 {place}。"
    station = nearest_station(
        float(located["latitude"]),
        float(located["longitude"]),
        load_stations(VISIBILITY_STATIONS_PATH),
    )
    try:
        rows = latest_visibility(fetch_text(VISIBILITY_CSV_URL))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _failed(exc)
    matched = [
        row
        for row in rows
        if row["Automatic Weather Station"] == station["name"]
    ]
    if not matched:
        return f"找到最近能见度站 {station['name']}，但当前能见度数据里没有该站。"
    row = matched[0]
    return (
        f"查询地名: {place}\n"
        f"匹配地点: {located['name']}\n"
        f"最近能见度站: {station['name']}\n"
        f"距离: 约 {float(station['distance_km']):.1f} 公里\n"
        f"最新十分钟平均能见度: {row['Date time']}\n"
        + _visibility_line(row)
    )


@mcp.tool()
def get_humidity(station: str = "") -> str:
    """返回各气象站最新一分钟平均相对湿度。

    station 可填英文站名的一部分，例如 Observatory 或 Sha Tin。
    留空则返回全部站点。
    """
    try:
        rows = latest_humidity(fetch_text(HUMIDITY_CSV_URL))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _failed(exc)
    if not rows:
        return "最新一分钟平均相对湿度: 无数据"

    query = station.strip().lower()
    if query:
        rows = [
            row
            for row in rows
            if query in row["Automatic Weather Station"].lower()
        ]
        if not rows:
            return f"没有找到名称包含 {station!r} 的湿度站。"

    observed_at = rows[0]["Date time"]
    lines = [
        f"- {row['Automatic Weather Station']}: {row['Relative Humidity(percent)']}%"
        for row in rows
    ]
    return f"最新一分钟平均相对湿度: {observed_at}\n" + "\n".join(lines)


@mcp.tool()
def get_nearest_humidity(place: str) -> str:
    """根据香港地名查找最近湿度站的最新一分钟平均相对湿度。

    place 是地区、车站或地标，例如黄埔、沙田、香港理工大学。
    只在提供相对湿度的气象站中找最近的一个。
    """
    located = geocode_place(place)
    if located is None:
        return f"没有找到地名 {place}。"
    station = nearest_station(
        float(located["latitude"]),
        float(located["longitude"]),
        load_stations(HUMIDITY_STATIONS_PATH),
    )
    try:
        rows = latest_humidity(fetch_text(HUMIDITY_CSV_URL))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _failed(exc)
    matched = [
        row
        for row in rows
        if row["Automatic Weather Station"] == station["name"]
    ]
    if not matched:
        return f"找到最近湿度站 {station['name']}，但当前湿度数据里没有该站。"
    row = matched[0]
    return (
        f"查询地名: {place}\n"
        f"匹配地点: {located['name']}\n"
        f"最近湿度站: {station['name']}\n"
        f"距离: 约 {float(station['distance_km']):.1f} 公里\n"
        f"最新一分钟平均相对湿度: {row['Date time']}\n"
        f"{station['name']}: {row['Relative Humidity(percent)']}%"
    )


def _uv_level(value: float) -> str:
    if value < 3:
        return "低"
    if value < 6:
        return "中"
    if value < 8:
        return "高"
    if value < 11:
        return "甚高"
    return "极高"


@mcp.tool()
def get_uv_index() -> str:
    """返回香港最新十五分钟平均紫外线指数。

    这是全港一个数值，不能按地区或气象站筛选。
    只在香港时间上午 7 时至下午 6 时更新。
    """
    try:
        row = latest_uv_index(fetch_text(UV_INDEX_CSV_URL))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _failed(exc)
    if not row:
        return "最新十五分钟平均紫外线指数: 无数据"
    raw = row["past 15-minute mean UV Index"].strip()
    try:
        level = _uv_level(float(raw))
        intensity = f"强度: {level}"
    except ValueError:
        intensity = "强度: 无法根据读数分级"
    return (
        "最新十五分钟平均紫外线指数（全港一个数值，不能按地区选择）\n"
        f"时间: {row['Date time']}\n"
        f"紫外线指数: {raw}\n"
        f"{intensity}\n"
        "更新时间: 香港时间上午 7 时至下午 6 时，每 15 分钟一次。"
    )


WEATHER_API = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"


def _weather_url(data_type: str) -> str:
    return f"{WEATHER_API}?dataType={data_type}&lang=sc"


def _format_local_forecast(data: dict) -> str:
    lines = []
    if data.get("forecastPeriod"):
        lines.append(str(data["forecastPeriod"]))
    if data.get("generalSituation"):
        lines.append(f"概况: {data['generalSituation']}")
    if data.get("forecastDesc"):
        lines.append(f"预测: {data['forecastDesc']}")
    if data.get("outlook"):
        lines.append(f"展望: {data['outlook']}")
    if data.get("tcInfo"):
        lines.append(f"热带气旋: {data['tcInfo']}")
    if data.get("fireDangerWarning"):
        lines.append(f"火灾危险警告: {data['fireDangerWarning']}")
    lines.append(f"更新时间: {data.get('updateTime', '未知')}")
    return "\n".join(lines)


def _format_nine_day_forecast(data: dict) -> str:
    lines = []
    if data.get("generalSituation"):
        lines.append(str(data["generalSituation"]))
    for day in data.get("weatherForecast") or []:
        high = (day.get("forecastMaxtemp") or {}).get("value", "未知")
        low = (day.get("forecastMintemp") or {}).get("value", "未知")
        lines.append(
            f"{day.get('forecastDate', '')} {day.get('week', '')}: "
            f"{day.get('forecastWeather', '')} {low}–{high}°C。"
            f"{day.get('forecastWind', '')}"
        )
    lines.append(f"更新时间: {data.get('updateTime', '未知')}")
    return "\n".join(lines)


def _format_current_report(data: dict) -> str:
    lines = [
        f"更新时间: {data.get('updateTime', '未知')}",
        f"香港天文台气温: {hko_temperature(data)}",
    ]
    for item in data.get("humidity", {}).get("data", []):
        if item.get("place") == "香港天文台":
            unit = "%" if item.get("unit") == "percent" else item.get("unit", "")
            lines.append(f"相对湿度: {item.get('value')}{unit}")
            break
    message = data.get("warningMessage") or ""
    if isinstance(message, list):
        message = " ".join(str(item) for item in message if item)
    lines.append(f"警告信息: {message or '无'}")
    return "\n".join(lines)


def _format_warning_details(data: dict) -> str:
    details = data.get("details") or []
    if not details:
        return "目前没有详细天气警告信息。"
    lines = []
    for item in details:
        contents = item.get("contents") or []
        text = "\n".join(contents) if isinstance(contents, list) else str(contents)
        code = item.get("warningStatementCode", "")
        lines.append(f"[{code}]\n{text}".strip())
    return "\n\n".join(lines)


def _format_special_tips(data: dict) -> str:
    tips = data.get("swt") or []
    if not tips:
        return "目前没有特别天气提示。"
    lines = []
    for tip in tips:
        lines.append(f"{tip.get('updateTime', '')}\n{tip.get('desc', '')}".strip())
    return "\n\n".join(lines)


@mcp.tool()
def get_weather_info(kind: str = "local_forecast") -> str:
    """查询香港天文台天气信息接口。

    kind 可选：
    local_forecast：本港地区天气预报；
    nine_day_forecast：九天天气预报；
    current：本港地区天气报告；
    warnings：天气警告一览；
    warning_details：详细天气警告信息；
    special_tips：特别天气提示。
    """
    formatters = {
        "local_forecast": ("flw", _format_local_forecast),
        "nine_day_forecast": ("fnd", _format_nine_day_forecast),
        "current": ("rhrread", _format_current_report),
        "warnings": ("warnsum", None),
        "warning_details": ("warningInfo", _format_warning_details),
        "special_tips": ("swt", _format_special_tips),
    }
    selected = formatters.get(kind)
    if selected is None:
        return "kind 只能是 local_forecast、nine_day_forecast、current、warnings、warning_details 或 special_tips。"
    data_type, formatter = selected
    try:
        data = fetch_json(_weather_url(data_type))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return _failed(exc)
    if kind == "warnings":
        lines = active_warnings(data)
        if not lines:
            return "正在生效的警告: 无"
        return "正在生效的警告:\n" + "\n".join(f"- {line}" for line in lines)
    return formatter(data)


if __name__ == "__main__":
    mcp.run()
