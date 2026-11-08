import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "hong-kong-places.md"
OUTPUT = Path(__file__).resolve().parent / "places.jsonl"


def split_places(markdown: str) -> list[dict]:
    district = ""
    kind = ""
    places: list[dict] = []
    current: dict | None = None

    def finish() -> None:
        nonlocal current
        if current is None:
            return
        current["text"] = "\n".join(current.pop("lines")).strip()
        places.append(current)
        current = None

    for raw in markdown.splitlines():
        line = raw.strip()
        if line.startswith("#### "):
            finish()
            current = {
                "district": district,
                "kind": kind,
                "name": line[5:].strip(),
                "latitude": None,
                "longitude": None,
                "section": "",
                "lines": [],
            }
            continue
        if line.startswith("### "):
            finish()
            kind = line[4:].strip()
            continue
        if line.startswith("## "):
            finish()
            title = line[3:].strip()
            if title != "目录":
                district = title
                kind = ""
            continue
        if current is None or not line or line.startswith("原文："):
            continue
        if line.startswith("- 坐标："):
            latitude, longitude = line.split("：", 1)[1].split(",")
            current["latitude"] = float(latitude)
            current["longitude"] = float(longitude)
            continue
        if line.startswith("- 章节："):
            current["section"] = line.split("：", 1)[1].strip()
            continue
        current["lines"].append(line)
    finish()
    return places


def main() -> None:
    places = split_places(SOURCE.read_text())
    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open("w") as f:
        for place in places:
            f.write(json.dumps(place, ensure_ascii=False) + "\n")
    missing = [place["name"] for place in places if place["latitude"] is None]
    print(f"切出 {len(places)} 块，写入 {OUTPUT}")
    if missing:
        print("没有坐标:", "、".join(missing))


if __name__ == "__main__":
    main()
