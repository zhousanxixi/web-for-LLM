# 网页查询

本地网页由 `python web_app.py` 启动，地址是 `http://127.0.0.1:8765`。页面在 `web/index.html`，表单和结果在 `web/app.js`，接口在 `web_app.py`。

左侧五个页面里，天气、附近美食、景点探索、港铁路线和列车到站会真正查询。出行助手走另一条接口，不经过下面的 `run_tool`。

## 共同调用链

查询页提交后，浏览器 `POST /api/query`，正文是 `{ "tool": "...", "arguments": { ... } }`。`query` 在线程里调用 `run_tool`，超时 130 秒。`run_tool` 按 `tool` 分发到普通 Python 函数，不经过 MCP。

```text
web/app.js requestForForm
  → POST /api/query
  → web_app.run_tool
  → queries 或 mcp_servers 里的函数
  → JSON { tool, elapsed_ms, result }
  → web/app.js renderResponse
```

`result.ok` 为假时，页面显示 `result.error.message`。成功时按工具名选卡片。附近美食和景点探索一页四条，结果全部返回，由浏览器分页。

## 天气与预报

请求工具名是 `get_weather`。`_weather` 再按 `kind` 调用 `mcp_servers/weather_server.py` 里的函数。这些函数和聊天用的是同一套，但网页是直接调用，不经过模型。

| 页面选项 | `kind` | 调用 |
|---|---|---|
| 当前天气报告 | `rhrread` | `get_weather_info("current")` |
| 本港天气预报 | `flw` | `get_weather_info("local_forecast")` |
| 九天预报 | `fnd` | `get_weather_info("nine_day_forecast")` |
| 正在生效的警告 | `warnsum` | `get_weather_info("warnings")` |
| 警告详情 | `warningInfo` | `get_weather_info("warning_details")` |
| 特别天气提示 | `swt` | `get_weather_info("special_tips")` |
| 全港紫外线 | `uv` | `get_uv_index()` |
| 当前气温 | `temperature` | 见下表 |
| 当前湿度 | `humidity` | 见下表 |
| 当前风向风速 | `wind` | 见下表 |
| 暑热指数 | `heat_index` | 见下表 |
| 能见度 | `visibility` | 见下表 |

全港报告和紫外线不使用地点。地点框只在气温、湿度、风速、暑热指数和能见度时出现。留空调用左边的全站函数；填写地名则调用右边的最近站函数。地名经 `util/geocode.py` 的 `geocode_place` 换成坐标。

| `kind` | 留空 | 填写地名 |
|---|---|---|
| `temperature` | `get_station_temperatures("")` | `get_nearest_temperature(place)` |
| `humidity` | `get_humidity("")` | `get_nearest_humidity(place)` |
| `wind` | `get_wind("")` | `get_nearest_wind(place)` |
| `heat_index` | `get_heat_index("")` | `get_nearest_heat_index(place)` |
| `visibility` | `get_visibility("")` | `get_nearest_visibility(place)` |

资料语言下拉框不会放进请求。天文台天气报告在 `get_weather_info` 里固定 `lang=sc`。各站 CSV 保持接口原有的站名语言。

返回是一段中文 `text`，页面放进「天气查询」卡片。说明里写「香港天文台」。接口和参数见 `weather_tool.md`。

## 附近美食

请求工具名是 `search_restaurants`。网页不传 `limit`，`_food` 使用 `0`，表示范围内有名字的店全部返回。

```text
web/app.js
  → web_app._food
  → queries/food.py collect_food
  → util/geocode.py geocode_place
  → util/overpass.py post_overpass
```

`collect_food` 把半径限制在 200 到 3000 米。类别来自 OpenStreetMap 的 `amenity`。选「全部饮食」时八类都查；否则只查所选的一类。查询语句只包含 `node`，建筑轮廓画成面的店不会出现。

| 选项 | `amenity` |
|---|---|
| 餐厅 | `restaurant` |
| 咖啡店 | `cafe` |
| 快餐 | `fast_food` |
| 美食广场 | `food_court` |
| 酒吧 | `bar` |
| 酒馆 | `pub` |
| 冰淇淋店 | `ice_cream` |
| 啤酒花园 | `biergarten` |

结果按直线距离排序。页面用 `pagedResults` 显示名称、类型、地址、距离和营业时间。说明包含匹配到的地名和 `© OpenStreetMap contributors`。

聊天里的 `get_nearby_food` 也调用 `collect_food`，但默认只取 8 条，而且不按网页上的类别筛选。交给模型的文字带坐标，不带地址。参数和返回格式见 `food_tool.md`。

## 景点探索

请求工具名是 `search_attractions`。同样不传 `limit`，范围内有名字的景点全部返回。这里不读 `knowledge/places.jsonl`。聊天里的景点检索仍然只用那份本地资料。

```text
web/app.js
  → web_app._attractions
  → queries/attractions.py collect_attractions
  → util/geocode.py geocode_place
  → util/overpass.py post_overpass
```

半径同样限制在 200 到 3000 米。类别是 `tourism`。选「所有景点」时用这六个值的正则；否则只查一个值。查询用 `nwr` 和 `out center`，点、线和面都会返回，面取中心点计算距离。

| 选项 | `tourism` |
|---|---|
| 景点 | `attraction` |
| 博物馆 | `museum` |
| 画廊 | `gallery` |
| 观景点 | `viewpoint` |
| 主题乐园 | `theme_park` |
| 动物园 | `zoo` |

没有名字的要素会被丢掉。页面一页四条，署名是 `© OpenStreetMap contributors`。

美食和景点都通过 `post_overpass` 依次尝试三个 Overpass 镜像。某一镜像返回的 `elements` 为空时，会换下一个镜像。

## 地铁查询

这一页有两个模式，由 `#transport-modes` 切换。

### 港铁路线

请求工具名是 `plan_mtr_route`。参数是出发站、目的站，以及是否允许机场快线。

```text
web/app.js
  → web_app._route
  → queries/mtr_route.py plan_mtr
  → util/mtr_stations.py 读取港铁站序 CSV
```

这是按官方站序规划换乘，不含步行、驾车、票价、预计时间和实时班次。返回的中文放进「港铁路线」卡片。规则见 `transport_tool.md` 的 `get_mtr_route`。网页直接调用 `plan_mtr`，不调用 `get_route`。

### 列车到站

请求工具名是 `get_mtr_arrivals`。参数是车站和线路代码。线路选「该站全部线路」时 `line` 为空。

```text
web/app.js
  → web_app._arrivals
  → queries/mtr_next.py collect_next_train
  → util/mtr_stations.py 把站名换成车站代码和线路
  → https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php
```

站名和线路对不上时，`collect_next_train` 在请求到站接口之前返回错误，例如「黄埔 不在荃湾线上。该站的线路是：观塘线。」对得上才按每条线请求班次。`lang` 固定为 `TC`；页面随界面语言附带的 `lang` 参数目前没有使用。

返回的 `data` 按线路放入 `UP` 和 `DOWN`。页面用 `mtrCard` 显示线路、方向、开往车站、月台和分钟数。某个方向没有班次时显示「这个方向现在没有班次」。说明是「资料来自港铁实时列车服务资讯。每个方向最多四班。」

## 出行助手

这一页不提交 `/api/query`。发送消息走 `POST /api/chat`，清空记录走 `POST /api/chat/reset`。服务启动时如果 `.env` 里有 `DEEPSEEK_API_KEY`，`/api/status` 的 `chat_available` 为真。

请求体仍然是 JSON。通过校验之后，响应不是一次返回的 JSON，而是 `application/x-ndjson`：每完成一步就输出一行。会话无效、没有钥匙或上一条还在处理时，仍直接返回 JSON 错误，不进入这串步骤。

```text
web/app.js streamChat
  → POST /api/chat
  → 每行一个事件
  → chat.prepare_question
  → chat.tools_for
  → chat.answer
  → MCP：weather_server、transport_server、food_server
```

页面在答案出现之前，就在港行助手头像下面展开「思考中」。事件有三种：

| `type` | 作用 |
|---|---|
| `step` | 一条思考步骤。`state` 为 `active` 时这一行闪烁，表示正在执行；为 `done` 时停止闪烁。同一个 `id` 可以先闪、再改成完成后的文字。 |
| `done` | 回答结束。带 `message` 和 `seconds`。页面停止闪烁，标题改为「思考 N秒」，然后显示正文。 |
| `error` | 这一轮失败。已出现的步骤停止闪烁，错误文字显示在助手名下。 |

判断问题类型、检索附近景点、调用工具和组织回答都会先以闪烁的一步出现，完成后再固定下来。命令行 `chat.py` 不走这条流，只在终端打印同样的步骤。

分类、景点资料和工具选择见 `chat.py`。天气工具见 `weather_tool.md`，交通工具见 `transport_tool.md`。网页上的景点 Overpass 和这里的本地景点库不是同一条链路。
