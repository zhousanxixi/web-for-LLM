"""港铁站序表。换乘规划和下一班车都读这份表，但互不调用。"""

import csv
from io import StringIO

from util.http_get import fetch_text

STATIONS_URL = "https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv"
LINE_NAMES = {
    "AEL": "机场快线",
    "TCL": "东涌线",
    "TML": "屯马线",
    "TKL": "将军澳线",
    "EAL": "东铁线",
    "SIL": "南港岛线",
    "TWL": "荃湾线",
    "ISL": "港岛线",
    "KTL": "观塘线",
    "DRL": "迪士尼线",
}
SIMPLIFIED = str.maketrans(
    {
        "灣": "湾",
        "東": "东",
        "門": "门",
        "馬": "马",
        "觀": "观",
        "島": "岛",
        "長": "长",
        "圍": "围",
        "錦": "锦",
        "啟": "启",
        "紅": "红",
        "羅": "罗",
        "車": "车",
        "機": "机",
        "鐘": "钟",
        "銅": "铜",
        "鑼": "锣",
        "鑽": "钻",
        "顯": "显",
        "黃": "黄",
        "龍": "龙",
        "樂": "乐",
        "寶": "宝",
        "將": "将",
        "藍": "蓝",
        "興": "兴",
        "學": "学",
        "會": "会",
        "廣": "广",
        "場": "场",
        "館": "馆",
        "臺": "台",
        "魚": "鱼",
        "鰂": "鲗",
        "調": "调",
        "嶺": "岭",
        "廟": "庙",
        "徑": "径",
        "園": "园",
        "環": "环",
        "運": "运",
        "恆": "恒",
        "國": "国",
        "華": "华",
        "書": "书",
        "麗": "丽",
        "豐": "丰",
        "綫": "线",
        "線": "线",
    }
)

_rows_cache: list[dict] | None = None


def _normalize(text: str) -> str:
    return "".join(text.translate(SIMPLIFIED).split()).lower()


def _load_rows() -> list[dict]:
    global _rows_cache
    if _rows_cache is None:
        text = fetch_text(STATIONS_URL).lstrip("\ufeff")
        _rows_cache = list(csv.DictReader(StringIO(text)))
    return _rows_cache
