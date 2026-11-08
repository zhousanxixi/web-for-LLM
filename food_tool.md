# Food 工具

`food` 是问题类型，不是工具名。这个类型只有一个 MCP 工具：`get_nearby_food`。

工具定义在 `mcp_servers/food_server.py`。取数在 `queries/food.py` 的 `nearby_food`，它再调用 `collect_food`。网页上的附近美食不经过这个 MCP 工具，而是直接调用 `collect_food`，见 `web_query.md`。

用户问附近吃什么、喝什么、餐厅、咖啡或美食时，分类结果会包含 `food`。`tools_for` 只把 `get_nearby_food` 交给模型。这个类型可以和天气、出行、交通同时出现。

## get_nearby_food

按直线距离查询香港某地附近的饮食地点。没有评分，也不确认是否正在营业。

| 参数 | 说明 |
|---|---|
| `place` | 地区、车站或地标，例如 `黄埔`。 |
| `radius_m` | 直线搜索半径，单位米。默认 `2000`。程序把它限制在 200 到 3000。 |
| `limit` | 返回条数。默认 `8`，最多 `15`。`0` 或负数表示不截断。 |

聊天调用时不传类别，八类都查。网页可以只查其中一类。

| 中文 | OpenStreetMap `amenity` |
|---|---|
| 餐厅 | `restaurant` |
| 咖啡店 | `cafe` |
| 快餐 | `fast_food` |
| 美食广场 | `food_court` |
| 酒吧 | `bar` |
| 酒馆 | `pub` |
| 冰淇淋店 | `ice_cream` |
| 啤酒花园 | `biergarten` |

## 调用过程

以「香港理工大学有什么好吃的」为例。

1. `chat.py` 把原问句单独发给模型做分类。结果含 `food` 时，`tools_for` 只留下 `get_nearby_food`。
2. 回答模型调用 `get_nearby_food`。终端打印 `[调用 get_nearby_food ...]`。
3. `geocode_place` 把地名换成经纬度。先请求 Nominatim，范围是香港的 viewbox；连不上或没有结果时改用 Photon。
4. `collect_food` 只查询点，不查询线和面。语句形如 `node["amenity"="restaurant"](around:半径,纬度,经度);`，八类放在同一个 Overpass 请求里。
5. `util/overpass.py` 的 `post_overpass` 把查询放在表单字段 `data` 里 POST。按顺序尝试下面三个地址，空结果或失败才换下一个。

```text
https://nominatim.openstreetmap.org/search
https://photon.komoot.io/api/
https://overpass.openstreetmap.fr/api/interpreter
https://overpass.osm.ch/api/interpreter
https://overpass.private.coffee/api/interpreter
```

没有店名，或没有坐标的元素会丢掉。同名且坐标四舍五入到小数点后四位相同的店只留一条。距离用直线距离，超过半径的不再保留。结果按距离、再按店名排序。

返回给模型的文字包含：查询地名、地理编码得到的地点全名、搜索半径，以及每家店的名称、类型、直线距离和坐标。有菜式或营业时间才写上。坐标写成 `纬度,经度`，只供模型判断位置。这段文字不包含地址。系统提示要求不要把坐标、经纬度和地址写给用户。

最后一行是 `数据 © OpenStreetMap contributors`。

网页上的附近美食用同一份 `collect_food`。它不传 `limit`，所以范围内有名字的店全部返回，页面再每页显示 4 条。卡片会显示地址；地址来自 `addr:full`，没有时用门牌和街道。聊天这条路径不把地址交给模型。
