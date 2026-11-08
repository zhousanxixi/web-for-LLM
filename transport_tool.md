# Transport 工具

`transport` 是问题类型，不是工具名。这个类型有三个 MCP 工具：`get_route`、`get_mtr_route` 和 `get_mtr_next_train`。

这三个工具都定义在 `mcp_servers/transport_server.py`。

- `get_route` 的取坐标和道路路线在 `queries/route.py`。钥匙写在项目目录的 `.env` 里，变量名是 `OPENROUTESERVICE_API_KEY`。
- `get_mtr_route` 的站序和换乘在 `queries/mtr_route.py`。它读取港铁公开的车站顺序表，不需要额外的钥匙。
- `get_mtr_next_train` 的到站班次在 `queries/mtr_next.py`。它请求港铁实时列车接口，不需要额外的钥匙。

## 什么时候用

用户问从一个地方到另一个地方怎么走、多远或要多久，或者问某站下一班车时，分类结果会包含 `transport`。`tools_for` 会留下 `get_route`、`get_mtr_route` 和 `get_mtr_next_train`，由回答模型按用户说的方式决定调哪一个。

| 用户怎么说 | 调用 |
|---|---|
| 没有说明交通方式，但给了起点和终点 | 同一轮调用两次：`get_route`（`mode` 为 `foot-walking`）和 `get_mtr_route`。不查驾车、骑行、徒步，也不查下一班车。 |
| 步行、驾车、骑行或徒步 | 只调用一次 `get_route`，`mode` 用对应的 profile。 |
| 地铁、港铁或 MTR，并给了起点和终点 | 只调用 `get_mtr_route`。 |
| 某站下一班车、两个方向、还有几分钟到站 | 只调用 `get_mtr_next_train`。 |

类型可以和其他类型同时出现。只要结果里有 `transport`，上面三个工具都会提供给模型；真正发出的调用仍按上一张表。

| 分类结果 | 这一轮还做什么 |
|---|---|
| 只有 `transport` | 不检索景点，不提供天气工具。 |
| `outing` 和 `transport` | 有地名时先检索附近景点，并提供全部天气工具。 |
| `weather` 和 `transport` | 同时提供天气工具，不检索景点。 |
| `food` 和 `transport` | 同时提供 `get_nearby_food`。 |

## 调用过程

以「从黄埔怎么去尖沙咀」为例。用户没有指定方式，所以步行和地铁都查。

1. `chat.py` 把原问句单独发给模型，只让它判断类型。这次判断不写入对话记录。结果是 `["transport"]`，没有地名。
2. `tools_for` 看到 `transport`，从全部工具里留下 `get_route`、`get_mtr_route` 和 `get_mtr_next_train`。
3. 回答模型在同一轮调用这两个工具。终端会先后打印 `[调用 get_route ...]` 和 `[调用 get_mtr_route ...]`。
4. `ToolClients` 按工具名把两次调用都交给路线服务，不交给天气服务或美食服务。
5. 两段文本都作为工具结果交回模型。模型按步行、地铁分段回答。步行保留每一步和米数；地铁按线路和车站顺序说明。

用户说了具体方式时，第 3 步只调用对应的那一个工具。

## get_route

查询香港两个地点之间的道路路线、距离和预计时间。不提供港铁、巴士或渡轮换乘。

| 参数 | 说明 |
|---|---|
| `origin` | 起点地名，例如 `黄埔`。 |
| `destination` | 终点地名，例如 `香港体育馆`。 |
| `mode` | 出行方式。不填时是 `foot-walking`。 |
| `origin_latitude`、`origin_longitude` | 可选。两个都有，并且落在北纬 22–23、东经 113.5–114.6 时，起点用这对坐标，不再按 `origin` 重新定位。地名仍用作结果里的起点名称。 |
| `destination_latitude`、`destination_longitude` | 可选。规则与起点相同。 |

某一端没有单独的纬度、经度，但地名本身是 `纬度,经度` 时，也直接用这对坐标。坐标超出上述范围，或只给了纬度、经度中的一个，就退回按地名做地理编码。

`mode` 可以写成下面任一列。中文别名会先换成右边的 profile，再放进请求地址。

| 说法 | profile | 含义 |
|---|---|---|
| `foot-walking`、`步行`、`walking` | `foot-walking` | 步行 |
| `driving-car`、`驾车`、`开车` | `driving-car` | 驾车 |
| `cycling-regular`、`骑行`、`单车` | `cycling-regular` | 骑行 |
| `foot-hiking`、`徒步` | `foot-hiking` | 徒步 |

处理步骤：

1. 某一端已经提供了可用坐标时，直接使用，不再地理编码。否则用 `util/geocode.py` 的 `geocode_place` 把地名换成经纬度。先请求 Nominatim，范围是香港的 viewbox；连不上或没有结果时改用 Photon。简体地名在 Photon 上会再试一次繁体，并只保留香港范围内的结果。
2. 向 OpenRouteService 发送 POST。坐标顺序是经度、纬度。请求头 `Authorization` 只放 API key，不加 `Bearer`。
3. 从返回的 GeoJSON 里取出总距离、总时间和每一步指引，整理成中文文本。

```text
https://nominatim.openstreetmap.org/search
https://photon.komoot.io/api/
https://api.heigit.org/openrouteservice/v2/directions/{profile}/geojson
```

返回给模型的文字包含：出行方式、起点和终点名称、整段距离、预计时间，以及全部逐步指引。按地名定位时，名称是地理编码得到的全名；直接用坐标时，名称仍是调用时给出的地名。地名本身就是坐标时，名称写成「指定位置」。每一步都保留米数，程序不会截断后面的步骤。距离不足 1 公里时用米，否则用公里。时间不足 1 小时时用分钟。

最后一行是 `路线数据 © OpenStreetMap contributors`。

## get_mtr_route

按港铁官方站序规划地铁路线。不含票价、预计时间和实时班次，也不含巴士。

| 参数 | 说明 |
|---|---|
| `origin` | 起点站名，例如 `黄埔`。简体可以识别。 |
| `destination` | 终点站名，例如 `中环`。 |
| `include_airport_express` | 是否把机场快线算进去。默认 `false`。 |

数据来自：

```text
https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv
```

程序把同一条线、同一方向上相邻的车站连成边，同一车站的不同线路算一次换乘。搜索时先少换乘，再少经过站。站名表是繁体，匹配前会把常见繁体字换成简体。机场快线默认不进入这张图。

尖沙咀和尖东、中环和香港站是不同站码，站外步行不计入路线。

返回文字包含起点、终点、按线路拆开的车站顺序和换乘站。最后说明站序来自港铁公开数据。

## get_mtr_next_train

查询一个港铁站接下来最多四班即将到站的列车。不能用来规划从起点到终点的换乘。

| 参数 | 说明 |
|---|---|
| `station` | 站名，例如 `金钟`。简体可以识别。 |
| `line` | 线路名，例如 `荃湾线`。用户没说线路时留空，会查询该站的每一条线。 |

数据来自：

```text
https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php
```

站名先用港铁站序表换成车站代码和线路代码，再请求上面的接口。同一条线的 `UP` 和 `DOWN` 是两个方向，每班写明开往哪一站、月台和大约还要几分钟。终点站可能只有一个方向。

最后一行是 `资料来自港铁实时列车服务资讯`。
