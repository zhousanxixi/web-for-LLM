# Weather 工具

工具定义在 `mcp_servers/weather_server.py`。模型决定调用哪一个；程序再去请求下面的接口。

带地名的工具通过 `util/geocode.py` 的 `geocode_place` 取坐标。先请求 Nominatim，范围是香港的 viewbox；连不上或没有结果时改用 Photon。简体地名在 Photon 上会再试一次繁体，并只保留香港范围内的结果。

```text
https://nominatim.openstreetmap.org/search
https://photon.komoot.io/api/
```

## get_station_temperatures

返回各自动气象站最新一分钟平均气温。

| 参数 | 说明 |
|---|---|
| `station` | 英文站名的一部分，例如 `Sha Tin`、`Observatory`。留空返回全部站点。 |

接口：

```text
https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_1min_temperature.csv
```

## get_nearest_temperature

把香港地名换成坐标，在 `station_info/temperature_station.csv` 里找最近的气象站，再返回该站最新一分钟平均气温。

| 参数 | 说明 |
|---|---|
| `place` | 地区、车站或地标，例如 `黄埔`、`沙田`、`香港理工大学`。 |

调用的接口和本地数据：

1. `geocode_place` 把地名换成经纬度。
2. `station_info/temperature_station.csv`：气象站名称和坐标。这一步不访问网络。
3. 与 `get_station_temperatures` 相同的分区气温 CSV，按最近站名取出气温。

## get_historical_max_temperature

返回某站历史记录中的最高日气温，以及出现日期。`year` 在取回数据后于本地筛选，不会作为请求参数发出。

| 参数 | 说明 |
|---|---|
| `station` | 天文台站号。默认 `CCH`（长洲）。天文台总部用 `HKO`。 |
| `year` | 四位年份。`0` 表示在全部历史记录中找最高值。 |

接口：

```text
https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&rformat=csv&station={station}
```

## get_heat_index

返回最近的十分钟平均香港暑热指数。数据为临时数据，约每十分钟更新。文件含最近十组读数，站名使用文件中的繁体写法。

| 参数 | 说明 |
|---|---|
| `station` | 站名的一部分，例如 `天文台`、`沙田`、`京士柏`。留空返回最新一组各站指数；填写后返回该站最近十组。 |

接口：

```text
https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/recent10_10min_hkhi_sc.csv
```

## get_nearest_heat_index

把香港地名换成坐标，只在提供暑热指数的十个气象站里找最近的一个，再返回该站最新十分钟平均暑热指数。

暑热指数站写在 `station_info/heat_index_station.csv`，列与 `temperature_station.csv` 相同：`name,latitude,longitude`。雙魚河和九龍灣不在气温站表里，所以不能直接复用气温站表。

| 参数 | 说明 |
|---|---|
| `place` | 地区、车站或地标，例如 `黄埔`、`沙田`、`香港理工大学`。 |

调用的接口和本地数据：

1. `geocode_place` 把地名换成经纬度。
2. `station_info/heat_index_station.csv`：暑热指数站名称和坐标。这一步不访问网络。
3. 与 `get_heat_index` 相同的暑热指数 CSV，按最近站名取出最新读数。

## get_wind

返回各气象站最新十分钟平均风向、平均风速和最高阵风。站名是英文。

| 参数 | 说明 |
|---|---|
| `station` | 英文站名的一部分，例如 `Cheung Chau`、`Kai Tak`。留空返回全部站点。 |

接口：

```text
https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_10min_wind.csv
```

## get_nearest_wind

把香港地名换成坐标，在 `station_info/wind_station.csv` 里找最近的风速站，再返回该站最新十分钟平均风向、平均风速和最高阵风。风速站和气温站不是同一组，天文台总部没有出现在这个风速文件里。

| 参数 | 说明 |
|---|---|
| `place` | 地区、车站或地标，例如 `黄埔`、`长洲`、`赤柱`。 |

调用的接口和本地数据：

1. `geocode_place` 把地名换成经纬度。
2. `station_info/wind_station.csv`：风速站名称和坐标。这一步不访问网络。
3. 与 `get_wind` 相同的风速 CSV，按最近站名取出风向和风速。

## get_visibility

返回中环、赤鱲角、西湾河和横澜岛的最新十分钟平均能见度。只有这四个站。

| 参数 | 说明 |
|---|---|
| `station` | 英文站名的一部分，例如 `Central`、`Waglan`。留空返回全部四个站点。 |

接口：

```text
https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=LTMV&lang=en&rformat=csv
```

## get_nearest_visibility

把香港地名换成坐标，在 `station_info/visibility_station.csv` 的四个能见度站里找最近的一个，再返回该站最新十分钟平均能见度。

| 参数 | 说明 |
|---|---|
| `place` | 地区、车站或地标，例如 `黄埔`、`赤柱`、`机场`。 |

调用的接口和本地数据：

1. `geocode_place` 把地名换成经纬度。
2. `station_info/visibility_station.csv`：能见度站名称和坐标。这一步不访问网络。
3. 与 `get_visibility` 相同的能见度 CSV，按最近站名取出能见度。

## get_humidity

返回各气象站最新一分钟平均相对湿度。文件大约每 10 分钟更新。站名是英文。有湿度的站比气温站少，坐标写在 `station_info/humidity_station.csv`。

| 参数 | 说明 |
|---|---|
| `station` | 英文站名的一部分，例如 `Observatory`、`Sha Tin`。留空返回全部站点。 |

接口：

```text
https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_1min_humidity.csv
```

## get_nearest_humidity

把香港地名换成坐标，在 `station_info/humidity_station.csv` 里找最近的湿度站，再返回该站最新一分钟平均相对湿度。

| 参数 | 说明 |
|---|---|
| `place` | 地区、车站或地标，例如 `黄埔`、`沙田`、`香港理工大学`。 |

调用的接口和本地数据：

1. `geocode_place` 把地名换成经纬度。
2. `station_info/humidity_station.csv`：湿度站名称和坐标。这一步不访问网络。
3. 与 `get_humidity` 相同的相对湿度 CSV，按最近站名取出湿度。

## get_uv_index

返回香港最新十五分钟平均紫外线指数。文件只有一行，是全港一个数值，不能按地区或气象站筛选。香港时间上午 7 时至下午 6 时、每 15 分钟更新一次。

没有参数。

接口：

```text
https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_15min_uvindex.csv
```

## get_weather_info

查询天文台天气信息接口。请求不能指定地点；`lang` 固定为 `sc`。

| 参数 `kind` | `dataType` | 作用 |
|---|---|---|
| `local_forecast` | `flw` | 本港地区天气预报。默认值。 |
| `nine_day_forecast` | `fnd` | 九天天气预报。 |
| `current` | `rhrread` | 本港地区天气报告，含天文台整点气温、湿度和警告信息。 |
| `warnings` | `warnsum` | 正在生效的天气警告一览。 |
| `warning_details` | `warningInfo` | 详细天气警告信息。 |
| `special_tips` | `swt` | 特别天气提示。 |

接口：

```text
https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType={dataType}&lang=sc
```
