import json
import os
import re
import ssl
import urllib.request
from pathlib import Path
from urllib.error import HTTPError

from dotenv import load_dotenv

from util.geocode import geocode_place

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DIRECTIONS_URL = (
    "https://api.heigit.org/openrouteservice/v2/directions/{profile}/geojson"
)
PROFILES = {
    "步行": "foot-walking",
    "walking": "foot-walking",
    "foot-walking": "foot-walking",
    "驾车": "driving-car",
    "开车": "driving-car",
    "driving-car": "driving-car",
    "骑行": "cycling-regular",
    "单车": "cycling-regular",
    "cycling-regular": "cycling-regular",
    "徒步": "foot-hiking",
    "foot-hiking": "foot-hiking",
}
PROFILE_LABELS = {
    "foot-walking": "步行",
    "driving-car": "驾车",
    "cycling-regular": "骑行",
    "foot-hiking": "徒步",
}
_COORDINATES = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*[,，]\s*(-?\d+(?:\.\d+)?)\s*$")


def _in_range(latitude: float, longitude: float) -> bool:
    return 22.0 <= latitude <= 23.0 and 113.5 <= longitude <= 114.6


def _locate(
    name: str, latitude: float | None = None, longitude: float | None = None
) -> dict | None:
    """有坐标时直接用坐标，否则按地名定位。"""
    if latitude is not None and longitude is not None:
        try:
            lat, lon = float(latitude), float(longitude)
        except (TypeError, ValueError):
            lat = lon = None
        if lat is not None and _in_range(lat, lon):
            return {
                "name": name.strip() or "指定位置",
                "latitude": lat,
                "longitude": lon,
            }
    match = _COORDINATES.match(name.strip())
    if match is not None:
        lat, lon = float(match.group(1)), float(match.group(2))
        if _in_range(lat, lon):
            return {"name": "指定位置", "latitude": lat, "longitude": lon}
    return geocode_place(name)


def _post_json(url: str, payload: dict, api_key: str) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
            "User-Agent": "hko-weather-demo/1.0 (student project)",
        },
        method="POST",
    )
    cafile = Path("/etc/ssl/cert.pem")
    context = (
        ssl.create_default_context(cafile=cafile)
        if cafile.exists()
        else ssl.create_default_context()
    )
    try:
        with urllib.request.urlopen(request, timeout=15, context=context) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"OpenRouteService returned HTTP {exc.code}") from exc


def _format_distance(meters: float) -> str:
    if meters >= 1000:
        return f"{meters / 1000:.1f} 公里"
    return f"{round(meters)} 米"


def _format_duration(seconds: float) -> str:
    minutes = round(seconds / 60)
    if minutes < 60:
        return f"{minutes} 分钟"
    hours, rest = divmod(minutes, 60)
    if rest == 0:
        return f"{hours} 小时"
    return f"{hours} 小时 {rest} 分钟"


def collect_route(
    origin,
    destination,
    mode="foot-walking",
    origin_latitude=None,
    origin_longitude=None,
    destination_latitude=None,
    destination_longitude=None,
):
    from concurrent.futures import ThreadPoolExecutor
    import math
    from urllib.parse import urlencode

    if (
        not origin.strip()
        or not destination.strip()
        or len(origin) > 120
        or len(destination) > 120
    ):
        return {
            "ok": False,
            "error": {"code": "INVALID_PLACE", "message": "请输入有效的起点和终点。"},
        }
    profile = PROFILES.get(mode.strip().lower(), PROFILES.get(mode.strip()))
    if profile is None:
        return {
            "ok": False,
            "error": {
                "code": "INVALID_MODE",
                "message": "请选择步行、驾车、骑行或徒步。",
            },
        }
    travelmode = {
        "foot-walking": "walking",
        "foot-hiking": "walking",
        "driving-car": "driving",
        "cycling-regular": "bicycling",
    }[profile]
    external = "https://www.google.com/maps/dir/?" + urlencode(
        {
            "api": 1,
            "origin": origin,
            "destination": destination,
            "travelmode": travelmode,
        }
    )
    for lat, lon in [
        (origin_latitude, origin_longitude),
        (destination_latitude, destination_longitude),
    ]:
        if (lat is None) != (lon is None):
            return {
                "ok": False,
                "error": {
                    "code": "INVALID_COORDINATES",
                    "message": "经纬度必须同时提供。",
                },
            }
        if lat is not None:
            try:
                if not (
                    math.isfinite(float(lat))
                    and math.isfinite(float(lon))
                    and _in_range(float(lat), float(lon))
                ):
                    raise ValueError()
            except (ValueError, TypeError):
                return {
                    "ok": False,
                    "error": {
                        "code": "INVALID_COORDINATES",
                        "message": "请提供香港范围内有效坐标。",
                    },
                }
    key = os.getenv("OPENROUTESERVICE_API_KEY", "").strip()
    if not key:
        return {
            "ok": False,
            "status": "not_configured",
            "external_url": external,
            "error": {
                "code": "ROUTING_NOT_CONFIGURED",
                "message": "站内路线暂不可用，可打开地图查看同一交通方式的路线。",
            },
            "notes": ["外部地图自行规划；本站未取得路线距离、时间或几何。"],
        }
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(_locate, origin, origin_latitude, origin_longitude)
            b = pool.submit(
                _locate, destination, destination_latitude, destination_longitude
            )
            start, end = a.result(), b.result()
        if not start or not end:
            return {
                "ok": False,
                "external_url": external,
                "error": {
                    "code": "PLACE_NOT_FOUND",
                    "message": "起点或终点未找到，请补充完整地名。",
                },
            }
        payload = {
            "coordinates": [
                [start["longitude"], start["latitude"]],
                [end["longitude"], end["latitude"]],
            ],
            "language": "zh-cn",
        }
        data = _post_json(DIRECTIONS_URL.format(profile=profile), payload, key)
        feature = (data.get("features") or [None])[0]
        if not feature:
            raise ValueError("No route")
        props = feature.get("properties") or {}
        summary = props.get("summary") or {}
        geometry = feature.get("geometry")
        if (
            not geometry
            or geometry.get("type") != "LineString"
            or not geometry.get("coordinates")
        ):
            raise ValueError("Missing route geometry")
        if not all(
            isinstance(summary.get(k), (int, float))
            and math.isfinite(summary[k])
            and summary[k] >= 0
            for k in ["distance", "duration"]
        ):
            raise ValueError("Missing route metrics")
        steps = [
            step
            for segment in props.get("segments", [])
            for step in segment.get("steps", [])
        ]
        return {
            "ok": True,
            "provider": "OpenRouteService",
            "source": "https://openrouteservice.org/",
            "external_url": external,
            "data": {
                "mode": profile,
                "origin": start,
                "destination": end,
                "distance_m": summary["distance"],
                "duration_s": summary["duration"],
                "geometry": geometry,
                "steps": steps,
            },
            "notes": [
                "路线和预计时间来自OpenRouteService，不包含实时路况或通行保证。",
                "© OpenStreetMap contributors; routing by openrouteservice",
            ],
        }
    except (OSError, TimeoutError, RuntimeError, ValueError):
        return {
            "ok": False,
            "external_url": external,
            "error": {
                "code": "ROUTING_UNAVAILABLE",
                "message": "路线服务暂不可用，请稍后重试或打开地图。",
            },
        }


def route_between(
    origin,
    destination,
    mode="foot-walking",
    origin_latitude=None,
    origin_longitude=None,
    destination_latitude=None,
    destination_longitude=None,
):
    result = collect_route(
        origin,
        destination,
        mode,
        origin_latitude,
        origin_longitude,
        destination_latitude,
        destination_longitude,
    )
    if not result.get("ok"):
        return json.dumps(result, ensure_ascii=False)
    d = result["data"]
    lines = [
        f"方式: {PROFILE_LABELS[d['mode']]}",
        f"起点: {d['origin']['name']}",
        f"终点: {d['destination']['name']}",
        f"距离: {_format_distance(d['distance_m'])}",
        f"预计时间: {_format_duration(d['duration_s'])}",
        "路线:",
    ]
    for i, step in enumerate(d["steps"], 1):
        lines.append(
            f"{i}. {step.get('instruction', '')} ({_format_distance(float(step.get('distance', 0)))})"
        )
    lines.extend(result["notes"])
    return "\n".join(lines)
