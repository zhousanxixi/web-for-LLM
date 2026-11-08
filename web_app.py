"""本地网页：python web_app.py"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from mcp.client import Client
from openai import APIError, OpenAI
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from vector_rag import search as search_knowledge, index_status
from queries.route import collect_route
from mcp_servers.knowledge_server import mcp as knowledge_mcp

from chat import (
    SYSTEM_PROMPT,
    ToolClients,
    answer,
    openai_tools,
    prepare_question,
    tools_for,
)
from queries.food import collect_food
from mcp_servers.food_server import mcp as food_mcp
from mcp_servers.transport_server import mcp as transport_mcp
from mcp_servers.weather_server import (
    get_heat_index,
    get_humidity,
    get_nearest_heat_index,
    get_nearest_humidity,
    get_nearest_temperature,
    get_nearest_visibility,
    get_nearest_wind,
    get_station_temperatures,
    get_uv_index,
    get_visibility,
    get_weather_info,
    get_wind,
    mcp as weather_mcp,
)
from queries.mtr_next import collect_next_train
from queries.mtr_route import plan_mtr
from queries.attractions import collect_attractions

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
SESSION_ID = re.compile(r"[a-zA-Z0-9_-]{8,80}\Z")
MAX_BODY = 16 * 1024
WEATHER_REPORTS = {
    "rhrread": "current",
    "flw": "local_forecast",
    "fnd": "nine_day_forecast",
    "warnsum": "warnings",
    "warningInfo": "warning_details",
    "swt": "special_tips",
}
UNAVAILABLE = {}


def api_error(message, code, status=400):
    return JSONResponse(
        {"error": {"code": code, "message": message}}, status_code=status
    )


def unavailable(name: str) -> dict:
    return {"ok": False, "error": {"message": UNAVAILABLE[name]}}


def text_result(text: str, *notes: str) -> dict:
    result = {"ok": True, "text": text}
    if notes:
        result["notes"] = list(notes)
    return result


def _weather(name: str, args: dict) -> dict:
    kind = str(args.get("kind") or "rhrread")
    place = str(
        args.get("place") or args.get("location") or args.get("station") or ""
    ).strip()
    if kind in WEATHER_REPORTS:
        return text_result(get_weather_info(WEATHER_REPORTS[kind]), "香港天文台")
    if kind == "uv":
        return text_result(get_uv_index(), "香港天文台")
    station_tools = {
        "temperature": (get_station_temperatures, get_nearest_temperature),
        "humidity": (get_humidity, get_nearest_humidity),
        "wind": (get_wind, get_nearest_wind),
        "heat_index": (get_heat_index, get_nearest_heat_index),
        "visibility": (get_visibility, get_nearest_visibility),
    }
    pair = station_tools.get(kind)
    if pair is None:
        return {"ok": False, "error": {"message": "这种天气资料还没接上。"}}
    whole, nearest = pair
    if place:
        return text_result(nearest(place), "香港天文台")
    return text_result(whole(""), "香港天文台")


def _food(args: dict) -> dict:
    place = str(args.get("location") or "").strip()
    if not place:
        return {"ok": False, "error": {"message": "请输入目的地。"}}
    radius = args.get("radius_m", 2000)
    limit = args.get("limit", 8)
    located, rows, error = collect_food(
        place,
        radius,
        limit,
        str(args.get("category") or "all"),
    )
    if error or located is None:
        return {"ok": False, "error": {"message": error or f"没有找到地名 {place}。"}}
    data = [
        {
            "name": row["name"],
            "address": " · ".join(
                part for part in (row["category"], row["address"]) if part
            ),
            "distance_m": row["meters"],
            "cuisine": row["cuisine"],
            "opening_hours_raw": row["hours"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "osm_url": f"https://www.openstreetmap.org/{row['osm_type']}/{row['osm_id']}",
        }
        for row in rows
    ]
    return {
        "ok": True,
        "provider": "OpenStreetMap",
        "data": data,
        "notes": [
            f"匹配地点：{located['name']}",
            "© OpenStreetMap contributors",
        ],
    }


def _attractions(args: dict) -> dict:
    place = str(args.get("location") or "").strip()
    if not place:
        return {"ok": False, "error": {"message": "请输入目的地。"}}
    located, rows, error = collect_attractions(
        place,
        args.get("radius_m", 1000),
        args.get("limit", 8),
        str(args.get("category") or "all"),
    )
    if error or located is None:
        return {"ok": False, "error": {"message": error or f"没有找到地名 {place}。"}}
    data = [
        {
            "name": row["name"],
            "address": " · ".join(
                part for part in (row["category"], row["address"]) if part
            ),
            "distance_m": row["meters"],
            "opening_hours_raw": row["hours"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "text": row["text"],
            "osm_url": f"https://www.openstreetmap.org/{row['osm_type']}/{row['osm_id']}",
        }
        for row in rows
    ]
    return {
        "ok": True,
        "provider": "OpenStreetMap",
        "data": data,
        "notes": [
            f"匹配地点：{located['name']}",
            "© OpenStreetMap contributors",
        ],
    }


def _route(args: dict) -> dict:
    origin = str(args.get("origin") or "").strip()
    destination = str(args.get("destination") or "").strip()
    if not origin or not destination:
        return {"ok": False, "error": {"message": "请输入出发站和目的站。"}}
    include = args.get("include_airport_express")
    if isinstance(include, str):
        include = include.lower() in {"1", "true", "yes"}
    return text_result(plan_mtr(origin, destination, bool(include)), "港铁公开站序")


def _arrivals(args: dict) -> dict:
    station = str(args.get("station") or "").strip()
    if not station:
        return {"ok": False, "error": {"message": "请输入港铁车站。"}}
    payload, error = collect_next_train(station, str(args.get("line") or ""))
    if error or payload is None:
        return {"ok": False, "error": {"message": error or "现在没有到站班次。"}}
    notes = ["资料来自港铁实时列车服务资讯。每个方向最多四班。"]
    if payload.get("message") not in {None, "", "successful"}:
        notes.append(payload["message"])
    return {
        "ok": True,
        "provider": "港铁",
        "data": payload,
        "destination_names": payload["destination_names"],
        "notes": notes,
    }


def run_tool(name: str, args: dict) -> dict:
    if name == "search_travel_knowledge":
        return search_knowledge(str(args.get("query", "")), int(args.get("limit", 5)))
    if name == "resolve_outing_request":
        from chat import classify_question

        kinds, place = classify_question(None, str(args.get("question", "")))
        return {
            "ok": True,
            "intents": kinds,
            "locations": [{"name": place}] if place else [],
            "preferences": [],
        }
    if name == "get_route":
        return collect_route(
            str(args.get("origin", "")),
            str(args.get("destination", "")),
            str(args.get("mode", "foot-walking")),
        )
    if name == "get_outing_overview":
        from concurrent.futures import ThreadPoolExecutor

        place = str(args.get("location", "")).strip()
        if not place:
            return {"ok": False, "error": {"message": "请输入目的地。"}}
        jobs = {"weather": lambda: _weather("get_weather", {"kind": "flw"})}
        if args.get("include_food", True):
            jobs["restaurants"] = lambda: _food(
                {"location": place, "radius_m": args.get("radius_m", 1000), "limit": 5}
            )
        if args.get("include_attractions", False):
            jobs["attractions"] = lambda: _attractions(
                {"location": place, "radius_m": args.get("radius_m", 1000), "limit": 5}
            )
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {k: pool.submit(fn) for k, fn in jobs.items()}
            data = {}
            for key, future in futures.items():
                try:
                    data[key] = future.result()
                except Exception:
                    data[key] = {
                        "ok": False,
                        "error": {"message": "此来源暂时不可用。"},
                    }
        failed = [k for k, v in data.items() if not v.get("ok")]
        return {
            "ok": len(failed) < len(data),
            "status": "error"
            if len(failed) == len(data)
            else "partial"
            if failed
            else "ok",
            "data": data,
            "failed_sections": failed,
            "notes": ["仅查询已选来源；各来源并行执行，单个失败不覆盖其他结果。"],
        }
    if name in {"get_weather", "get_place_weather", "get_station_weather"}:
        return _weather(name, args)
    if name == "search_restaurants":
        return _food(args)
    if name == "search_attractions":
        return _attractions(args)
    if name == "plan_mtr_route":
        return _route(args)
    if name == "get_mtr_arrivals":
        return _arrivals(args)
    return {"ok": False, "error": {"message": "这个查询还没接上。"}}


class TracingClient:
    def __init__(self, services: ToolClients):
        self.services = services
        self.events: list[dict] = []

    async def call_tool(self, name: str, arguments: dict):
        try:
            result = await self.services.call_tool(name, arguments)
        except Exception:
            self.events.append({"tool": name, "status": "error"})
            raise
        self.events.append({"tool": name, "status": "ok"})
        return result


async def read_json(request: Request) -> dict:
    if (
        request.headers.get("content-type", "").split(";")[0].strip()
        != "application/json"
    ):
        raise ValueError("请使用 application/json 发送请求。")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BODY:
            raise ValueError("请求过大，请缩短输入。")
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("请求不是有效 JSON。") from exc
    if not isinstance(data, dict):
        raise ValueError("请求必须为 JSON 对象。")
    return data


async def index(_request):
    return FileResponse(WEB / "index.html")


async def status(request):
    return JSONResponse(
        {
            "ok": True,
            "chat_available": request.app.state.llm is not None,
            "tool_count": len(request.app.state.tool_defs),
            "rag": index_status(),
            "routing_available": bool(os.getenv("OPENROUTESERVICE_API_KEY")),
        }
    )


async def query(request):
    try:
        body = await read_json(request)
    except ValueError as exc:
        return api_error(str(exc), "INVALID_BODY")
    name, args = body.get("tool"), body.get("arguments", {})
    if not isinstance(name, str) or not isinstance(args, dict):
        return api_error("工具名称或参数无效。", "INVALID_TOOL")
    start = time.monotonic()
    try:
        async with request.app.state.query_slots:
            result = await asyncio.wait_for(
                asyncio.to_thread(run_tool, name, args), timeout=45
            )
    except TimeoutError:
        return api_error("查询超时，请缩小范围后重试。", "TIMEOUT", 504)
    except Exception:
        return api_error("查询暂时失败，请重试或查看终端。", "QUERY_ERROR", 502)
    return JSONResponse(
        {
            "tool": name,
            "elapsed_ms": round((time.monotonic() - start) * 1000),
            "result": result,
        }
    )


def session_key(body: dict) -> str:
    key = body.get("session_id")
    if not isinstance(key, str) or not SESSION_ID.fullmatch(key):
        raise ValueError("会话标识无效，请刷新页面。")
    return key


class LiveNotes:
    """把进行中的步骤推到网页，同时保留完成后的文字。"""

    def __init__(self, loop, queue: asyncio.Queue):
        self.lines: list[str] = []
        self.loop = loop
        self.queue = queue
        self.closed = False
        self._seq = 0
        self._pending: dict[int, str] = {}

    def _emit(self, payload: dict) -> None:
        if self.closed:
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is self.loop:
            self.queue.put_nowait(payload)
        else:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, payload)

    def begin(self, text: str) -> int:
        self._seq += 1
        ident = self._seq
        self._pending[ident] = text
        self._emit({"type": "step", "id": ident, "text": text, "state": "active"})
        return ident

    def end(self, ident: int, text: str | None = None) -> None:
        final = self._pending.pop(ident, text or "")
        if text is not None:
            final = text
        self.lines.append(final)
        self._emit({"type": "step", "id": ident, "text": final, "state": "done"})

    def evidence(self, result):
        self._emit({"type": "evidence", "retrieval": result})

    def token(self, text):
        self._emit({"type": "token", "text": text})

    def clear_tokens(self):
        self._emit({"type": "clear_tokens"})

    def append(self, line: str) -> None:
        self.lines.append(line)
        self._seq += 1
        self._emit({"type": "step", "id": self._seq, "text": line, "state": "done"})


async def chat(request):
    try:
        body = await read_json(request)
        key = session_key(body)
        message = body.get("message", "")
        language = body.get("language", "zh")
        if not isinstance(language, str) or language not in {"zh", "en"}:
            raise ValueError("Unsupported language.")
        if not isinstance(message, str) or not message.strip() or len(message) > 3000:
            raise ValueError("请输入 1–3000 字的问题。")
    except ValueError as exc:
        return api_error(str(exc), "INVALID_BODY")
    state = request.app.state
    if state.llm is None:
        return api_error(
            "尚未配置 DeepSeek API key。请在项目 .env 中配置后重启网页服务。",
            "CHAT_NOT_CONFIGURED",
            503,
        )
    sessions = state.chat_sessions
    now = time.monotonic()
    for sid, item in list(sessions.items()):
        if now - item["last_used"] > 3600 and not item["lock"].locked():
            sessions.pop(sid, None)
    if key not in sessions:
        if len(sessions) >= 20:
            return api_error("会话数量已达上限，请稍后重试。", "SESSION_LIMIT", 429)
        sessions[key] = {
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "lock": asyncio.Lock(),
            "last_used": now,
        }
    item = sessions[key]
    if item["lock"].locked():
        return api_error("上一条消息还在处理中。", "CHAT_BUSY", 409)
    await item["lock"].acquire()
    queue: asyncio.Queue = asyncio.Queue()
    notes = LiveNotes(asyncio.get_running_loop(), queue)

    async def work() -> None:
        try:
            item["last_used"] = time.monotonic()
            tracer = TracingClient(state.services)
            started = time.monotonic()
            try:
                kinds, content = await asyncio.to_thread(
                    prepare_question, state.llm, message.strip(), notes
                )
                if language == "en":
                    content += "\nPlease answer this turn in English, retaining source links and units."
                reply = await asyncio.wait_for(
                    answer(
                        tracer,
                        state.llm,
                        tools_for(kinds, state.tool_defs),
                        item["messages"],
                        content,
                        notes,
                    ),
                    timeout=180,
                )
            except TimeoutError:
                await queue.put(
                    {"type": "error", "message": "本轮回答超时，请缩小问题范围。"}
                )
            except APIError:
                await queue.put(
                    {
                        "type": "error",
                        "message": "模型服务请求失败，请检查 .env 和账户状态。",
                    }
                )
            except Exception:
                traceback.print_exc()
                await queue.put(
                    {"type": "error", "message": "本轮回答未完成，请重试。"}
                )
            else:
                await queue.put(
                    {
                        "type": "done",
                        "message": reply,
                        "seconds": max(1, round(time.monotonic() - started)),
                    }
                )
        finally:
            notes.closed = True
            item["lock"].release()
            await queue.put(None)

    task = asyncio.create_task(work())

    async def generate():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=10)
                except TimeoutError:
                    yield json.dumps({"type": "heartbeat"}) + "\n"
                    continue
                if event is None:
                    break
                yield json.dumps(event, ensure_ascii=False) + "\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def reset_chat(request):
    try:
        key = session_key(await read_json(request))
    except ValueError as exc:
        return api_error(str(exc), "INVALID_BODY")
    sessions = request.app.state.chat_sessions
    item = sessions.get(key)
    if item and item["lock"].locked():
        return api_error("回答处理中，请稍后清空。", "CHAT_BUSY", 409)
    sessions.pop(key, None)
    return JSONResponse({"ok": True})


@asynccontextmanager
async def lifespan(app):
    load_dotenv(ROOT / ".env")
    app.state.chat_sessions = {}
    app.state.query_slots = asyncio.Semaphore(4)
    key = os.getenv("DEEPSEEK_API_KEY")
    app.state.llm = (
        OpenAI(
            api_key=key,
            base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
            timeout=40,
            max_retries=0,
        )
        if key
        else None
    )
    async with (
        Client(weather_mcp) as weather_client,
        Client(transport_mcp) as transport_client,
        Client(food_mcp) as food_client,
        Client(knowledge_mcp) as knowledge_client,
    ):
        services = ToolClients(
            [weather_client, transport_client, food_client, knowledge_client]
        )
        app.state.services = services
        app.state.tool_defs = openai_tools(await services.open())
        yield
        app.state.chat_sessions.clear()


def create_app():
    return Starlette(
        lifespan=lifespan,
        routes=[
            Route("/", index),
            Route("/api/status", status),
            Route("/api/query", query, methods=["POST"]),
            Route("/api/chat", chat, methods=["POST"]),
            Route("/api/chat/reset", reset_chat, methods=["POST"]),
            Mount("/static", StaticFiles(directory=WEB), name="static"),
        ],
    )


def main():
    import uvicorn

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print(f"\n打开浏览器：http://127.0.0.1:{args.port}\n按 Ctrl+C 关闭网页服务。\n")
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
