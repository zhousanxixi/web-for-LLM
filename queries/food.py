from urllib.error import URLError

from util.geocode import geocode_place
from util.nearest_station import distance_km
from util.overpass import post_overpass

CATEGORIES = {
    "restaurant": "餐厅",
    "cafe": "咖啡店",
    "fast_food": "快餐",
    "food_court": "美食广场",
    "bar": "酒吧",
    "pub": "酒馆",
    "ice_cream": "冰淇淋店",
    "biergarten": "啤酒花园",
}


def collect_food(
    place: str,
    radius_m: int = 2000,
    limit: int = 8,
    category: str = "all",
) -> tuple[dict | None, list[dict], str | None]:
    """返回定位结果、按距离排序的店，或一条错误说明。"""
    located = geocode_place(place)
    if located is None:
        return None, [], f"没有找到地名 {place}。"
    radius_m = min(max(int(radius_m), 200), 3000)
    try:
        raw_limit = int(limit)
    except (TypeError, ValueError):
        raw_limit = 0
    lat = float(located["latitude"])
    lon = float(located["longitude"])
    kinds = (category,) if category in CATEGORIES else tuple(CATEGORIES)
    clauses = "".join(
        f'nwr["amenity"="{amenity}"](around:{radius_m},{lat:.6f},{lon:.6f});'
        for amenity in kinds
    )
    query = f"[out:json][timeout:25];({clauses});out center;"
    try:
        data = post_overpass(query)
    except (OSError, URLError, TimeoutError, RuntimeError, ValueError) as exc:
        return located, [], f"获取附近美食失败: {exc}"

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
        rows.append(
            {
                "name": name,
                "category": CATEGORIES.get(
                    tags.get("amenity"), tags.get("amenity") or "饮食"
                ),
                "meters": round(meters),
                "latitude": float(point["lat"]),
                "longitude": float(point["lon"]),
                "address": tags.get("addr:full")
                or " ".join(
                    part
                    for part in (tags.get("addr:housenumber"), tags.get("addr:street"))
                    if part
                ),
                "hours": tags.get("opening_hours") or "",
                "cuisine": tags.get("cuisine") or "",
                "osm_type": element.get("type") or "node",
                "osm_id": element.get("id"),
            }
        )
    rows.sort(key=lambda item: (item["meters"], item["name"]))
    selected = rows[: min(max(raw_limit, 1), 15)] if raw_limit > 0 else rows[:8]
    if not selected:
        label = CATEGORIES.get(category, "饮食地点")
        return (
            located,
            [],
            f"在 {located['name']} 周围 {radius_m} 米内没有找到{label}。",
        )
    return located, selected, None


def nearby_food(place: str, radius_m: int = 2000, limit: int = 8) -> str:
    """按直线距离查询香港某地附近的餐厅和饮食店。"""
    located, selected, error = collect_food(place, radius_m, limit)
    if error or located is None:
        return error or f"没有找到地名 {place}。"

    lines = [
        f"查询地名: {place}",
        f"匹配地点: {located['name']}",
        f"范围: {radius_m} 米内，按直线距离排序",
        "坐标仅供定位，不要向用户展示坐标或地址。",
    ]
    for item in selected:
        detail = [
            f"名称: {item['name']}",
            f"类型: {item['category']}",
            f"距离: 约 {item['meters']} 米",
            f"坐标: {item['latitude']:.6f}, {item['longitude']:.6f}",
        ]
        if item["cuisine"]:
            detail.append(f"菜式: {item['cuisine']}")
        if item["hours"]:
            detail.append(f"营业时间: {item['hours']}")
        lines.append("\n".join(detail))
    lines.append("数据 © OpenStreetMap contributors")
    return "\n\n".join(lines)
