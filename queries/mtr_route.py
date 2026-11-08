import heapq
from collections import defaultdict
from itertools import count

from util.mtr_stations import LINE_NAMES, _load_rows, _normalize


def _network(include_airport_express: bool) -> tuple[dict, dict, dict]:
    grouped = defaultdict(list)
    names = {}
    lines = defaultdict(set)
    for row in _load_rows():
        line = row["Line Code"]
        code = row["Station Code"]
        if line not in LINE_NAMES or (line == "AEL" and not include_airport_express):
            continue
        names[code] = _normalize(row["Chinese Name"])
        lines[code].add(line)
        grouped[(line, row["Direction"])].append((float(row["Sequence"]), code))

    graph = defaultdict(dict)
    for (line, _), ordered in grouped.items():
        stations = []
        seen = set()
        for _, code in sorted(ordered):
            if code not in seen:
                seen.add(code)
                stations.append(code)
        for left, right in zip(stations, stations[1:]):
            graph[(left, line)][(right, line)] = 1
            graph[(right, line)][(left, line)] = 1
    for code, station_lines in lines.items():
        for left in station_lines:
            for right in station_lines:
                if left != right:
                    graph[(code, left)][(code, right)] = 0
    return graph, names, lines


def _match(query: str, names: dict) -> str | None:
    key = _normalize(query)
    exact = [
        code
        for code, name in names.items()
        if key in {name, code.lower()}
    ]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None
    partial = [code for code, name in names.items() if key and key in name]
    if len(partial) == 1:
        return partial[0]
    return None


def _match_label(query: str, names: dict) -> str:
    key = _normalize(query)
    partial = [names[code] for code, name in names.items() if key and key in name]
    unique = sorted(set(partial))
    if not unique:
        return f"没有找到港铁站「{query}」。请使用站名，例如黄埔、中环。"
    shown = "、".join(unique[:8])
    return f"「{query}」对应多个车站：{shown}。请写出完整站名。"


def plan_mtr(origin: str, destination: str, include_airport_express: bool = False) -> str:
    """按港铁官方站序规划地铁路线。不含票价、耗时和实时班次。"""
    try:
        graph, names, lines = _network(include_airport_express)
    except (OSError, TimeoutError, ValueError) as exc:
        return f"获取港铁站序失败: {exc}"

    start = _match(origin, names)
    goal = _match(destination, names)
    if start is None:
        return _match_label(origin, names)
    if goal is None:
        return _match_label(destination, names)
    if start == goal:
        return f"{names[start]} 就是起点，不需要乘车。"

    queue = []
    best = {}
    ticket = count()
    for line in sorted(lines[start]):
        node = (start, line)
        best[node] = (0, 0)
        heapq.heappush(queue, ((0, 0), next(ticket), node, [node]))

    path = None
    while queue:
        cost, _, node, route = heapq.heappop(queue)
        if cost != best.get(node):
            continue
        if node[0] == goal:
            path = route
            break
        for neighbor, ride in graph[node].items():
            transfer = 0 if neighbor[1] == node[1] else 1
            updated = (cost[0] + transfer, cost[1] + ride)
            if updated < best.get(neighbor, (10**9, 10**9)):
                best[neighbor] = updated
                heapq.heappush(queue, (updated, next(ticket), neighbor, [*route, neighbor]))
    if path is None:
        return "在现有港铁站序里没有找到路线。机场快线默认不计入。"

    segments = []
    for code, line in path:
        if not segments or segments[-1]["line"] != line:
            segments.append({"line": line, "stations": [names[code]]})
        elif names[code] != segments[-1]["stations"][-1]:
            segments[-1]["stations"].append(names[code])

    lines_out = [
        f"起点: {names[start]}",
        f"终点: {names[goal]}",
        "路线按港铁官方站序规划，先少换乘，再少经过站。不含票价、预计时间和实时班次。",
    ]
    for index, segment in enumerate(segments, start=1):
        station_text = " → ".join(segment["stations"])
        lines_out.append(f"{index}. {LINE_NAMES[segment['line']]}：{station_text}")
    if len(segments) > 1:
        transfers = "、".join(segment["stations"][0] for segment in segments[1:])
        lines_out.append(f"换乘站: {transfers}")
    else:
        lines_out.append("换乘站: 无")
    lines_out.append("站序数据来自港铁公开数据。尖沙咀和尖东、中环和香港站这类不同站码之间的步行没有计入。")
    return "\n".join(lines_out)
