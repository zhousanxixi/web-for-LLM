# 返回输入地点的坐标
import json
import time
import threading
from util.cache import ttl_cache
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.error import URLError

from util.http_get import fetch_text

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PHOTON_URL = "https://photon.komoot.io/api/"
USER_AGENT = "hko-weather-demo/1.0 (student project)"
# Photon 对简体「黄埔」会先命中广州。查询失败时改用繁体再限定香港。
TO_TRADITIONAL = str.maketrans(
    "湾东门马观岛长围锦启红罗车机钟铜锣钻显黄龙乐宝将蓝兴学会广场馆台鱼鲗调岭庙径园环运恒国华书丽丰线",
    "灣東門馬觀島長圍錦啟紅羅車機鐘銅鑼鑽顯黃龍樂寶將藍興學會廣場館臺魚鰂調嶺廟徑園環運恆國華書麗豐線",
)


def _place(name: str, latitude: float, longitude: float) -> dict:
    return {
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
    }


_NOMINATIM_LOCK = threading.Lock()
_LAST_CALL = 0.0


def _nominatim(query: str) -> dict | None:
    global _LAST_CALL
    url = (
        NOMINATIM_URL
        + "?"
        + urllib.parse.urlencode(
            {
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                # 香港在 OpenStreetMap 里常标为中国，countrycodes=hk 会把结果滤掉。
                "viewbox": "113.82,22.57,114.51,22.13",
                "bounded": 1,
            }
        )
    )
    with _NOMINATIM_LOCK:
        wait = 1.05 - (time.monotonic() - _LAST_CALL)
        if wait > 0:
            time.sleep(wait)
        _LAST_CALL = time.monotonic()
        results = json.loads(fetch_text(url, timeout=6, user_agent=USER_AGENT))
    if not results:
        return None
    place = results[0]
    return _place(
        place.get("display_name", ""), float(place["lat"]), float(place["lon"])
    )


def _photon(query: str) -> dict | None:
    """Nominatim 连不上时，用 Photon 在香港范围内找同名地点。"""
    variants = [query]
    traditional = query.translate(TO_TRADITIONAL)
    if traditional != query:
        variants.append(traditional)
    cafile = Path("/etc/ssl/cert.pem")
    context = (
        ssl.create_default_context(cafile=cafile)
        if cafile.exists()
        else ssl.create_default_context()
    )
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context),
    )
    for text in variants:
        url = (
            PHOTON_URL
            + "?"
            + urllib.parse.urlencode(
                {"q": text, "limit": 15, "lat": 22.32, "lon": 114.17}
            )
        )
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with opener.open(request, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError, ValueError):
            continue
        for feature in data.get("features") or []:
            lon, lat = feature.get("geometry", {}).get("coordinates") or (None, None)
            if lat is None or lon is None:
                continue
            props = feature.get("properties") or {}
            region = " ".join(
                str(props.get(key) or "")
                for key in ("state", "city", "county", "country", "name")
            )
            if "Hong Kong" not in region and "香港" not in region:
                continue
            if not (113.82 <= float(lon) <= 114.51 and 22.13 <= float(lat) <= 22.57):
                continue
            return _place(props.get("name") or query, float(lat), float(lon))
    return None


@ttl_cache()
def geocode_place(name: str) -> dict | None:
    """把香港地名换成经纬度。找不到时返回 None。"""
    query = name.strip()
    aliases = {
        "香港理工": "香港理工大學",
        "理工": "香港理工大學",
        "香港理工大学": "香港理工大學",
        "polyu": "香港理工大學",
        "黄埔": "黃埔花園",
        "whampoa": "黃埔花園",
        "tst": "尖沙咀",
        "尖沙嘴": "尖沙咀",
    }
    query = aliases.get(query.lower(), query)
    if not query:
        return None
    if "香港" not in query and "Hong Kong" not in query:
        query = f"{query},香港"
    try:
        located = _nominatim(query)
    except (URLError, TimeoutError, OSError, ValueError):
        located = None
    if located is not None:
        return located
    return _photon(query)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("用法: python geocode.py 黄埔")
    place = geocode_place(" ".join(sys.argv[1:]))
    if place is None:
        print("没有找到这个地名")
        return
    print(place["name"])
    print(f"{place['latitude']:.6f}, {place['longitude']:.6f}")


if __name__ == "__main__":
    main()
