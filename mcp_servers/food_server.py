import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp.server import MCPServer

from queries.food import nearby_food

mcp = MCPServer(
    "Hong Kong Food",
    instructions=(
        "查询香港某地附近的餐厅、咖啡店、快餐、美食广场、酒吧、酒馆、冰淇淋店和啤酒花园。"
        "问附近吃什么、喝什么或美食时，调用 get_nearby_food。"
        "结果来自 OpenStreetMap，没有评分。"
    ),
)


@mcp.tool()
def get_nearby_food(place: str, radius_m: int = 2000, limit: int = 8) -> str:
    """查询香港地名附近的饮食地点。

    place 是地区、车站或地标，例如黄埔。
    radius_m 是直线搜索半径，默认 2000 米。
    limit 是返回条数，默认 8。
    数据来自 OpenStreetMap，没有评分或实时营业确认。
    """
    return nearby_food(place, radius_m, limit)


if __name__ == "__main__":
    mcp.run()
