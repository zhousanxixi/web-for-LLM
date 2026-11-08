"""Offline retrieval evaluation; no paid LLM calls."""

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vector_rag import search, index_status

cases = [
    ("黄埔属于哪个区", ["黄埔"]),
    ("雨天带小孩去室内玩", ["科学馆"]),
    ("wheelchair access museum", ["无障碍"]),
    ("Hong Kong art museum", ["Hong Kong Museum of Art"]),
    ("远足天气查询", ["远足"]),
    ("tea ware museum", ["Flagstaff House Museum of Tea Ware"]),
]
rows = []
for question, expected in cases:
    started = time.perf_counter()
    result = search(question, 5)
    rank = next(
        (
            i
            for i, d in enumerate(result["data"], 1)
            if any(word in d["name"] for word in expected)
        ),
        None,
    )
    rows.append(
        {
            "query": question,
            "expected": expected,
            "method": result["method"],
            "rank": rank,
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "retrieved": [d["name"] for d in result["data"]],
        }
    )
print(
    json.dumps(
        {
            "index": index_status(),
            "cases": rows,
            "hit_at_5": sum(r["rank"] is not None for r in rows) / len(rows),
            "mrr_at_5": sum(1 / r["rank"] if r["rank"] else 0 for r in rows)
            / len(rows),
            "notes": "Six hand-authored smoke cases only, not a representative benchmark or proof of answer accuracy.",
        },
        ensure_ascii=False,
        indent=2,
    )
)
