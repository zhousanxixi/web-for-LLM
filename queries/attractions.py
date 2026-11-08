"""网页景点探索：按 OpenStreetMap Overpass 查询，不读本地景点库。"""

from util.geocode import geocode_place
from util.nearest_station import distance_km
from util.overpass import post_overpass

TOURISM = {
    "attraction": "景点",
    "museum": "博物馆",
    "gallery": "画廊",
    "viewpoint": "观景点",
    "theme_park": "主题乐园",
    "zoo": "动物园",
}


def collect_attractions(
    place: str,
    radius_m: int = 1000,
    limit: int = 8,
    category: str = "all",
) -> tuple[dict | None, list[dict], str | None]:
    """返回定位结果、按距离排序的景点，或一条错误说明。"""
    try:
        located = geocode_place(place)
    except (OSError, TimeoutError, ValueError) as exc:
        return None, [], f"地名定位失败: {exc}"
    if located is None:
        return None, [], f"没有找到地名 {place}。"
    radius_m = min(max(int(radius_m), 200), 3000)
    try:
        raw_limit = int(limit)
    except (TypeError, ValueError):
        raw_limit = 0
    lat = float(located["latitude"])
    lon = float(located["longitude"])
    if category in TOURISM:
        selector = f'["tourism"="{category}"]'
    else:
        kinds = "|".join(TOURISM)
        selector = f'["tourism"~"^({kinds})$"]'
    query = (
        f"[out:json][timeout:5];"
        f"(nwr{selector}(around:{radius_m},{lat:.6f},{lon:.6f}););"
        f"out center;"
    )
    try:
        data = post_overpass(query)
    except (OSError, TimeoutError, RuntimeError, ValueError) as exc:
        return None, [], f"获取附近景点失败: {exc}"

    rows = []
    seen = set()
    for element in data.get("elements") or []:
        tags = element.get("tags") or {}
        point = element if "lat" in element else element.get("center") or {}
        name = tags.get("name:zh") or tags.get("name") or tags.get("name:en")
        if not name or "lat" not in point or "lon" not in point:
            continue
        identity = (name, round(float(point["lat"]), 4), round(float(point["lon"]), 4))
        if identity in seen:
            continue
        seen.add(identity)
        meters = distance_km(lat, lon, float(point["lat"]), float(point["lon"])) * 1000
        if meters > radius_m:
            continue
        kind = tags.get("tourism") or ""
        address = tags.get("addr:full") or " ".join(
            part
            for part in (tags.get("addr:housenumber"), tags.get("addr:street"))
            if part
        )
        rows.append(
            {
                "name": name,
                "category": TOURISM.get(kind, kind or "景点"),
                "meters": round(meters),
                "latitude": float(point["lat"]),
                "longitude": float(point["lon"]),
                "address": address,
                "hours": tags.get("opening_hours") or "",
                "text": tags.get("description:zh") or tags.get("description") or "",
                "osm_type": element.get("type") or "node",
                "osm_id": element.get("id"),
            }
        )
    rows.sort(key=lambda item: (item["meters"], item["name"]))
    rows = rows[: min(raw_limit, 15)] if raw_limit > 0 else rows[:8]
    if not rows:
        return located, [], f"在 {located['name']} 周围 {radius_m} 米内没有找到景点。"
    return located, rows, None
