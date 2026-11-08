# 2026-11-09 更新

已加入向量RAG、流式进度、OSM美食查询优化与多方式地图路线。启动与配置见 [UPGRADE.md](UPGRADE.md)，知识库见 [RAG.md](RAG.md)。

# 香港天气与出行

用 DeepSeek 回答香港的天气、附近美食、景点和交通问题。`chat.py` 通过 MCP 调用实时数据。`chat_plain.py` 只调用模型，不查外部数据，用来对比。网页用 `python web_app.py` 打开，地址是 http://127.0.0.1:8765 。

下面的命令都在本目录 `demo_learn` 里运行。系统自带的 `python3` 没有这些依赖，所以使用 `.venv/bin/python`。

工具参数和调用过程见 `weather_tool.md`、`food_tool.md`、`transport_tool.md`、`web_query.md` 和 `RAG.md`。

## 准备

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

在本目录创建 `.env`。不要提交到 git。

```bash
DEEPSEEK_API_KEY=你的钥匙
OPENROUTESERVICE_API_KEY=你的钥匙 #去这个网站注册key，免费的：https://account.heigit.org/signup
```

`DEEPSEEK_API_KEY` 用于命令行聊天和网页上的出行助手。`OPENROUTESERVICE_API_KEY` 只用于 `get_route` 的步行、驾车、骑行和徒步路线。天文台、港铁、OpenStreetMap 和 Overpass 不需要钥匙。

## 网页

```bash
.venv/bin/python web_app.py
```

打开 http://127.0.0.1:8765 。首页是出行助手。左侧还有天气与预报、附近美食、景点探索和地铁查询。

| 页面 | 做什么 |
|---|---|
| 出行助手 | 把问题发给 DeepSeek。回答出现前，头像下面会逐步显示判断、景点检索和工具调用，当前那一步会闪。模型按问题类型调用 MCP 工具。点「新对话」会删掉服务器上这一份消息记录，下一句不再接着上一轮。 |
| 天气与预报 | 直接请求天文台。不经过模型。 |
| 附近美食 | 用 Overpass 查周围的餐厅和饮食店，按直线距离分页显示。 |
| 景点探索 | 用 Overpass 查周围的景点。聊天里的景点不走这里，而是读本地 `knowledge/places.jsonl`。 |
| 地铁查询 | 港铁路线按官方站序规划换乘。列车到站查询接下来最多四班。没有巴士查询。 |

查询页直接调用 Python 函数，不经过 MCP。改完代码后需要重新运行 `web_app.py`。

## 命令行

只检查天文台接口是否通：

```bash
.venv/bin/python -m queries.fetch_weather
```

会打印整点气温、生效警告、RSS 公报，以及各站气温、暑热指数、风、能见度、湿度和紫外线。

问一句。程序会显示判断出的类型和调用了哪个工具：

```bash
.venv/bin/python chat.py "天文台现在多少度"
```

连续对话。同一进程里的问题共用一份 `messages`，所以可以接着问。输入 `exit` 或 `quit` 结束。再次运行 `chat.py` 会新建一份只有系统提示的列表。

```bash
.venv/bin/python chat.py
```

可以试这几句：

- `天文台现在多少度`
- `现在有没有天气警告`
- `沙田现在多少度`
- `尖沙咀附近有什么吃的`
- `从黄埔怎么去尖沙咀`
- `金钟站下一班车`

不用 MCP、只让模型自己回答：

```bash
.venv/bin/python chat_plain.py "天文台现在多少度"
```

单独启动 MCP Server 会停住且没有输出。服务器在等宿主从标准输入连接。日常使用不需要单独启动，`chat.py` 和 `web_app.py` 会在同一进程里连上这些服务器。

```bash
.venv/bin/python mcp_servers/weather_server.py
```

## 文件

| 路径 | 作用 |
|---|---|
| `chat.py` | 命令行聊天。判断问题类型，把工具结果交回 DeepSeek。 |
| `chat_plain.py` | 只把问题发给 DeepSeek，不调用工具。 |
| `web_app.py` | 网页服务。查询页直接取数；出行助手复用 `chat.py` 里的函数。 |
| `web/` | 页面、样式和脚本。 |
| `mcp_servers/weather_server.py` | 十三个天气工具。 |
| `mcp_servers/transport_server.py` | `get_route`、`get_mtr_route`、`get_mtr_next_train`。 |
| `mcp_servers/food_server.py` | `get_nearby_food`。 |
| `queries/` | 天气、美食、景点、道路路线、港铁路线和列车到站的取数函数。 |
| `util/` | 共用的 HTTP、地理编码、Overpass、气象站距离和港铁站表。 |
| `knowledge/places.jsonl` | 聊天用的景点资料。网页景点探索不读这份文件。 |
| `station_info/` | 气象站坐标，用来按地名找最近的站。 |

## 天气工具

这些工具定义在 `mcp_servers/weather_server.py`。网页上的天气页调用同一套函数。

- `get_weather_info`：天气信息接口。`current` 是当前报告，`warnings` 是生效警告，另有本港预报、九天预报、详细警告和特别提示。
- `get_station_temperatures`：各站最新一分钟平均气温。可传入英文站名的一部分，例如 `Observatory`。
- `get_nearest_temperature`：按地名找最近气象站，并返回该站气温。
- `get_historical_max_temperature`：某站往年最高日气温。站号默认 `CCH`（长洲），天文台总部用 `HKO`。`year` 为 0 时查全部历史，填四位年份时只查该年。网页下拉框里没有这一项。
- `get_heat_index`：最近的十分钟平均香港暑热指数。留空返回最新一组各站；传入站名的一部分则返回该站最近十组。
- `get_nearest_heat_index`：按地名在十个暑热指数站里找最近的一个，并返回该站最新指数。
- `get_wind`：各站最新十分钟平均风向、平均风速和最高阵风。可传入英文站名的一部分。
- `get_nearest_wind`：按地名在风速站里找最近的一个，并返回该站风向和风速。
- `get_visibility`：中环、赤鱲角、西湾河和横澜岛的最新十分钟平均能见度。可传入英文站名的一部分。
- `get_nearest_visibility`：按地名在这四个能见度站里找最近的一个，并返回该站能见度。
- `get_humidity`：各站最新一分钟平均相对湿度。可传入英文站名的一部分。
- `get_nearest_humidity`：按地名在湿度站里找最近的一个，并返回该站相对湿度。
- `get_uv_index`：全港最新十五分钟平均紫外线指数。不能按地区选择。上午 7 时至下午 6 时更新。

数据来自香港天文台：

- 整点天气 JSON：`dataType=rhrread`
- 生效警告 JSON：`dataType=warnsum`
- 英文天气公报 RSS：`CurrentWeather.xml`
- 分区气温 CSV：`latest_1min_temperature.csv`
- 历年日最高气温 CSV：`dataType=CLMMAXT`，例如 `station=CCH`
- 香港暑热指数 CSV：`recent10_10min_hkhi_sc.csv`
- 十分钟风向风速 CSV：`latest_10min_wind.csv`
- 十五分钟紫外线指数 CSV：`latest_15min_uvindex.csv`
- 一分钟相对湿度 CSV：`latest_1min_humidity.csv`
- 十分钟能见度 CSV：`opendata.php?dataType=LTMV`

地名先经 OpenStreetMap Nominatim 换成坐标；连不上或没有结果时再用 Photon。范围限制在香港。
