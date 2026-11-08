"""港铁下一班车。只查某站即将到站的列车，不规划换乘。"""

import json
import ssl
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.error import URLError

from util.http_get import fetch_text
from util.mtr_stations import LINE_NAMES, _load_rows, _normalize

SCHEDULE_URL = "https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php"
LINE_BY_NAME = {code: code for code in LINE_NAMES}
LINE_BY_NAME.update({_normalize(name): code for code, name in LINE_NAMES.items()})


def _stations() -> dict[str, dict]:
    found = {}
    for row in _load_rows():
        line = row["Line Code"]
        code = row["Station Code"]
        if line not in LINE_NAMES:
            continue
        item = found.setdefault(
            code,
            {
                "zh": _normalize(row["Chinese Name"]),
                "en": " ".join((row.get("English Name") or "").split()).lower(),
                "lines": set(),
            },
        )
        item["lines"].add(line)
    return found


def _match_station(query: str, stations: dict[str, dict]) -> str | None:
    key = _normalize(query)
    english = " ".join(query.split()).lower()
    exact = [
        code
        for code, item in stations.items()
        if key in {item["zh"], code.lower()} or english == item["en"]
    ]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None
    partial = [code for code, item in stations.items() if key and key in item["zh"]]
    if len(partial) == 1:
        return partial[0]
    return None


def _station_hint(query: str, stations: dict[str, dict]) -> str:
    key = _normalize(query)
    names = sorted({item["zh"] for item in stations.values() if key and key in item["zh"]})
    if not names:
        return f"没有找到港铁站「{query}」。请使用站名，例如金钟、中环。"
    return f"「{query}」对应多个车站：{'、'.join(names[:8])}。请写出完整站名。"


def _match_line(query: str) -> str | None:
    key = _normalize(query)
    if not key:
        return None
    if key.upper() in LINE_NAMES:
        return key.upper()
    return LINE_BY_NAME.get(key)


def _fetch_schedule(line: str, station: str) -> dict:
    url = SCHEDULE_URL + "?" + urllib.parse.urlencode(
        {"line": line, "sta": station, "lang": "TC"}
    )
    try:
        return json.loads(fetch_text(url))
    except (URLError, TimeoutError, OSError, ValueError):
        cafile = Path("/etc/ssl/cert.pem")
        context = (
            ssl.create_default_context(cafile=cafile)
            if cafile.exists()
            else ssl.create_default_context()
        )
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=context),
        )
        request = urllib.request.Request(url, headers={"User-Agent": "hko-weather-demo/1.0"})
        with opener.open(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))


def _direction_lines(trains: list[dict], stations: dict[str, dict]) -> list[str]:
    if not trains:
        return ["这个方向现在没有班次。"]
    lines = []
    for train in trains:
        dest = train.get("dest") or ""
        dest_name = stations.get(dest, {}).get("zh") or dest
        minutes = str(train.get("ttnt") or "")
        when = "即将到站" if minutes == "0" else f"约 {minutes} 分钟"
        valid = "" if train.get("valid") == "Y" else "，资料待确认"
        lines.append(
            f"{train.get('seq', '')}. 开往{dest_name}，{train.get('plat', '')} 号月台，{when}{valid}"
            + (f"，预计 {train.get('time')}" if train.get("time") else "")
        )
    return lines


def _resolve(station: str, line: str = "") -> tuple[dict, str, list[str]] | tuple[None, None, str]:
    """返回车站表、车站代码和要查询的线路；无法查询时返回错误说明。"""
    stations = _stations()
    code = _match_station(station, stations)
    if code is None:
        return None, None, _station_hint(station, stations)
    item = stations[code]
    chosen = _match_line(line) if line.strip() else None
    if line.strip() and chosen is None:
        return None, None, f"没有找到线路「{line}」。请使用观塘线、荃湾线这样的线路名。"
    if chosen and chosen not in item["lines"]:
        available = "、".join(LINE_NAMES[line_code] for line_code in sorted(item["lines"]))
        return None, None, f"{item['zh']} 不在{LINE_NAMES[chosen]}上。该站的线路是：{available}。"
    targets = [chosen] if chosen else sorted(item["lines"])
    return stations, code, targets


def collect_next_train(station: str, line: str = "") -> tuple[dict | None, str | None]:
    """返回适合网页展示的到站资料，或一条错误说明。"""
    try:
        resolved = _resolve(station, line)
    except (OSError, TimeoutError, ValueError) as exc:
        return None, f"获取港铁站名失败: {exc}"
    if resolved[0] is None:
        return None, resolved[2]
    stations, code, targets = resolved
    combined = {
        "status": 1,
        "message": "successful",
        "isdelay": "N",
        "curr_time": "",
        "sys_time": "",
        "data": {},
        "destination_names": {item_code: item["zh"] for item_code, item in stations.items()},
    }
    errors = []
    for line_code in targets:
        try:
            payload = _fetch_schedule(line_code, code)
        except (OSError, TimeoutError, ValueError, URLError) as exc:
            errors.append(f"{LINE_NAMES[line_code]}：获取下一班车失败: {exc}")
            continue
        if str(payload.get("status")) == "0":
            errors.append(f"{LINE_NAMES[line_code]}：{payload.get('message') or '暂时没有班次资料'}")
            continue
        if payload.get("isdelay") == "Y":
            combined["isdelay"] = "Y"
        schedule = dict((payload.get("data") or {}).get(f"{line_code}-{code}") or {})
        schedule["line"] = line_code
        schedule["line_name"] = LINE_NAMES[line_code]
        combined["data"][f"{line_code}-{code}"] = schedule
        for key in ("curr_time", "sys_time"):
            value = payload.get(key)
            if value and value != "-":
                combined[key] = value
    if not combined["data"]:
        return None, errors[0] if errors else "现在没有到站班次。"
    if errors:
        combined["message"] = "；".join(errors)
    return combined, None


def next_train(station: str, line: str = "") -> str:
    """查询某港铁站接下来最多四班车。line 为空时查询该站所有线路。"""
    try:
        resolved = _resolve(station, line)
    except (OSError, TimeoutError, ValueError) as exc:
        return f"获取港铁站名失败: {exc}"
    if resolved[0] is None:
        return resolved[2]
    stations, code, targets = resolved
    item = stations[code]
    blocks = [
        f"车站: {item['zh']}",
        "这是即将到站的列车，不是从起点到终点的换乘路线。每个方向最多四班。",
    ]
    delay = False
    for line_code in targets:
        try:
            payload = _fetch_schedule(line_code, code)
        except (OSError, TimeoutError, ValueError, URLError) as exc:
            blocks.append(f"{LINE_NAMES[line_code]}：获取下一班车失败: {exc}")
            continue
        if str(payload.get("status")) == "0":
            blocks.append(f"{LINE_NAMES[line_code]}：{payload.get('message') or '暂时没有班次资料'}")
            continue
        if payload.get("isdelay") == "Y":
            delay = True
        schedule = (payload.get("data") or {}).get(f"{line_code}-{code}") or {}
        blocks.append(f"{LINE_NAMES[line_code]}")
        blocks.append("UP:")
        blocks.extend(_direction_lines(schedule.get("UP") or [], stations))
        blocks.append("DOWN:")
        blocks.extend(_direction_lines(schedule.get("DOWN") or [], stations))
        if payload.get("sys_time") and payload.get("sys_time") != "-":
            blocks.append(f"资料时间: {payload['sys_time']}")
    if delay:
        blocks.append("官方资料显示有延误。")
    blocks.append("资料来自港铁实时列车服务资讯。")
    return "\n".join(blocks)
