import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp.server import MCPServer

from queries.mtr_next import next_train
from queries.mtr_route import plan_mtr
from queries.route import route_between

mcp = MCPServer(
    "Hong Kong Transport",
    instructions=(
        "提供香港两个地点之间的路线。"
        "步行、驾车、骑行或徒步用 get_route。"
        "用户要坐地铁或港铁并给出起点和终点时，用 get_mtr_route。这是按官方站序规划，不含实时班次。"
        "用户问某站下一班车或还有几分钟到站时，用 get_mtr_next_train。"
    ),
)


@mcp.tool()
def get_route(
    origin: str,
    destination: str,
    mode: str = "foot-walking",
    origin_latitude: float | None = None,
    origin_longitude: float | None = None,
    destination_latitude: float | None = None,
    destination_longitude: float | None = None,
) -> str:
    """查询香港两个地点之间的路线、距离和预计时间。

    origin 是起点地名，destination 是终点地名。
    某一端如果同时提供了纬度和经度，就用这对坐标，不再按该端地名重新定位。
    mode 可选 foot-walking（步行）、driving-car（驾车）、
    cycling-regular（骑行）、foot-hiking（徒步）。
    不提供港铁、巴士或渡轮换乘。
    """
    return route_between(
        origin,
        destination,
        mode,
        origin_latitude,
        origin_longitude,
        destination_latitude,
        destination_longitude,
    )


@mcp.tool()
def get_mtr_route(
    origin: str,
    destination: str,
    include_airport_express: bool = False,
) -> str:
    """按港铁官方站序规划地铁路线。

    origin 是起点站名，destination 是终点站名，例如黄埔、中环。
    include_airport_express 为真时才把机场快线算进去。
    不含票价、预计时间和实时到站。
    """
    return plan_mtr(origin, destination, include_airport_express)


@mcp.tool()
def get_mtr_next_train(station: str, line: str = "") -> str:
    """查询某港铁站接下来最多四班即将到站的列车。

    station 是站名，例如金钟、黄埔、中环。
    line 是线路名，例如荃湾线、观塘线。用户没说线路时留空，会返回该站每一条线。
    同一条线的 UP 和 DOWN 是两个方向，以每班车的「开往」车站区分。
    不能用来规划从起点站到终点站的换乘。
    """
    return next_train(station, line)


if __name__ == "__main__":
    mcp.run()
