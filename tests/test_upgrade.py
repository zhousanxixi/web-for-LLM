import asyncio, io, json, os, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch, Mock
from urllib.error import HTTPError
import vector_rag as rag
from chat import answer, classify_question, tools_for
from queries.food import collect_food
from queries.route import collect_route
from util import overpass


class VectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.index = Path(self.temp.name) / "vectors.db"
        self.docs = [
            {
                "id": "rain",
                "chunk_id": "rain:0",
                "name": "rain",
                "text": "Indoor museum wheelchair access",
                "source": "https://example.org/rain",
                "kind": "guide",
            },
            {
                "id": "walk",
                "chunk_id": "walk:0",
                "name": "walk",
                "text": "Outdoor hiking mountain",
                "source": "https://example.org/walk",
                "kind": "guide",
            },
        ]
        self.p = patch("vector_rag.load_documents", return_value=self.docs)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.temp.cleanup()

    def build(self):
        return rag.build_index(
            "test", "test", self.index, encoder=lambda texts: [[1, 0], [0, 1]]
        )

    def test_persistence_and_sources(self):
        self.assertEqual(self.build()["dimension"], "2")
        r = rag.search("indoor", index=self.index, query_encoder=lambda q: [1, 0])
        self.assertIn("hybrid", r["method"])
        self.assertEqual(r["data"][0]["id"], "rain")
        self.assertIn("source", r["data"][0])

    def test_stale_fallback(self):
        self.build()
        self.docs[0]["text"] = "Changed museum"
        self.assertIn("fallback", rag.search("museum", index=self.index)["method"])

    def test_dimension_fallback(self):
        self.build()
        self.assertIn(
            "fallback",
            rag.search("museum", index=self.index, query_encoder=lambda q: [1, 0, 0])[
                "method"
            ],
        )

    def test_no_match_validation(self):
        self.assertEqual(
            rag.search("zzzznonexistent", index=self.index)["status"], "no_match"
        )
        for q, n in [("", 5), ("x", 0), ("x", 11)]:
            with self.assertRaises(ValueError):
                rag.search(q, n, index=self.index)
        with self.assertRaises(ValueError):
            rag.build_index(
                "test", "test", self.index, encoder=lambda texts: [[0, 0], [1, 0]]
            )

    def test_geo_filter(self):
        self.docs[0].update(latitude=22.3, longitude=114.17)
        self.docs[1].update(latitude=23.5, longitude=114.17)
        self.assertEqual(
            [
                d["id"]
                for d in rag.search(
                    "museum hiking",
                    index=self.index,
                    center={"latitude": 22.3, "longitude": 114.17},
                )["data"]
            ],
            ["rain"],
        )


class DataTests(unittest.TestCase):
    def setUp(self):
        overpass._CACHE.clear()
        overpass._COOLDOWN.clear()

    def test_empty_overpass_cached_no_mirror_loop(self):
        with patch(
            "util.overpass.urllib.request.urlopen",
            return_value=io.BytesIO(b'{"elements":[]}'),
        ) as send:
            overpass.post_overpass("empty")
            overpass.post_overpass("empty")
            self.assertEqual(send.call_count, 1)

    def test_rate_limit_not_bypassed(self):
        with patch(
            "util.overpass.urllib.request.urlopen",
            side_effect=HTTPError("https://example.org", 429, "limited", {}, None),
        ) as send:
            with self.assertRaises(RuntimeError):
                overpass.post_overpass("limited")
            self.assertEqual(send.call_count, 1)

    def test_food_includes_ways(self):
        data = {
            "elements": [
                {
                    "type": "way",
                    "id": 1,
                    "center": {"lat": 22.3, "lon": 114.17},
                    "tags": {"name": "Cafe", "amenity": "cafe"},
                }
            ]
        }
        with (
            patch(
                "queries.food.geocode_place",
                return_value={"name": "Polyu", "latitude": 22.3, "longitude": 114.17},
            ),
            patch("queries.food.post_overpass", return_value=data) as send,
        ):
            _, rows, error = collect_food("Polyu")
            self.assertIsNone(error)
            self.assertEqual(rows[0]["osm_type"], "way")
            self.assertIn("nwr[", send.call_args.args[0])

    def test_route_missing_key_and_invalid_coords(self):
        with patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": ""}):
            r = collect_route("Polyu", "TST", "driving-car")
            self.assertFalse(r["ok"])
            self.assertIn("travelmode=driving", r["external_url"])
            self.assertNotIn("data", r)
        self.assertFalse(collect_route("a", "b", origin_latitude=22.3)["ok"])
        self.assertFalse(collect_route("a", "b", mode="flying")["ok"])

    def test_geojson_metrics_coordinate_order(self):
        data = {
            "features": [
                {
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[114.17, 22.3], [114.18, 22.31]],
                    },
                    "properties": {
                        "summary": {"distance": 1000, "duration": 800},
                        "segments": [
                            {"steps": [{"instruction": "Walk", "distance": 1000}]}
                        ],
                    },
                }
            ]
        }
        with (
            patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "fake-test-only"}),
            patch(
                "queries.route._locate",
                side_effect=[
                    {"name": "a", "latitude": 22.3, "longitude": 114.17},
                    {"name": "b", "latitude": 22.31, "longitude": 114.18},
                ],
            ),
            patch("queries.route._post_json", return_value=data) as send,
        ):
            r = collect_route("a", "b")
            self.assertTrue(r["ok"])
            self.assertEqual(r["data"]["distance_m"], 1000)
            self.assertEqual(send.call_args.args[1]["coordinates"][0], [114.17, 22.3])

    def test_missing_metrics_not_zero(self):
        data = {
            "features": [
                {
                    "geometry": {"type": "LineString", "coordinates": [[114, 22]]},
                    "properties": {},
                }
            ]
        }
        with (
            patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "fake-test-only"}),
            patch(
                "queries.route._locate",
                return_value={"name": "a", "latitude": 22.3, "longitude": 114.17},
            ),
            patch("queries.route._post_json", return_value=data),
        ):
            self.assertFalse(collect_route("a", "b")["ok"])


def chunk(text=None, calls=None):
    return NS(choices=[NS(delta=NS(content=text, tool_calls=calls or []))])


def call(i, name, args):
    return NS(
        index=i, id="call" + str(i), function=NS(name=name, arguments=json.dumps(args))
    )


class Stream:
    def __init__(self, items):
        self.items = items

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __iter__(self):
        return iter(self.items)


class ChatTests(unittest.IsolatedAsyncioTestCase):
    def test_local_classification_and_selection(self):
        self.assertEqual(
            classify_question(None, "香港理工有什么好吃的"), (["food"], "香港理工大学")
        )
        tools = [
            {"function": {"name": n}}
            for n in [
                "get_weather_info",
                "get_route",
                "get_nearby_food",
                "search_travel_knowledge",
            ]
        ]
        self.assertEqual(
            [t["function"]["name"] for t in tools_for(["food"], tools)],
            ["get_nearby_food", "search_travel_knowledge"],
        )

    def test_mcp_only_disables_retrieval_tool(self):
        with patch.dict(os.environ, {"ENABLE_RAG": "0"}):
            tools = [
                {"function": {"name": name}}
                for name in ["get_nearby_food", "search_travel_knowledge"]
            ]
            self.assertEqual(
                [t["function"]["name"] for t in tools_for(["food"], tools)],
                ["get_nearby_food"],
            )

    async def test_parallel_tools_and_stream(self):
        streams = [
            Stream(
                [
                    chunk(
                        calls=[
                            call(0, "get_nearby_food", {"place": "Polyu"}),
                            call(1, "get_weather_info", {}),
                        ]
                    )
                ]
            ),
            Stream([chunk("Hello "), chunk("world")]),
        ]
        llm = NS(chat=NS(completions=NS(create=Mock(side_effect=streams))))
        entered = []
        both = asyncio.Event()

        async def invoke(name, args):
            entered.append(name)
            if len(entered) == 2:
                both.set()
            await asyncio.wait_for(both.wait(), timeout=1)
            return NS(content=[NS(text="verified")])

        messages = [{"role": "system", "content": "test"}]
        tools = [
            {"function": {"name": n}} for n in ["get_nearby_food", "get_weather_info"]
        ]
        self.assertEqual(
            await answer(NS(call_tool=invoke), llm, tools, messages, "question"),
            "Hello world",
        )
        self.assertEqual(len(entered), 2)
        self.assertEqual(messages[-1]["content"], "Hello world")

    async def test_failed_turn_does_not_poison_history(self):
        llm = NS(chat=NS(completions=NS(create=Mock(side_effect=RuntimeError("fail")))))
        messages = [{"role": "system", "content": "test"}]
        with self.assertRaises(RuntimeError):
            await answer(None, llm, [], messages, "question")
        self.assertEqual(len(messages), 1)


class SemanticTests(unittest.TestCase):
    def test_real_multilingual_embeddings(self):
        if not rag.index_status().get("vector_ready"):
            self.skipTest("Build vector index first")
        for q, name in [
            ("黄埔属于哪个区", "黄埔"),
            ("wheelchair access museum", "无障碍"),
            ("Hong Kong art museum", "Hong Kong Museum of Art"),
        ]:
            r = rag.search(q, 3)
            self.assertIn("hybrid", r["method"])
            self.assertTrue(any(name in d["name"] for d in r["data"]), q)


class WebTests(unittest.TestCase):
    def test_real_mcp_static_and_helpers(self):
        from starlette.testclient import TestClient
        from web_app import create_app

        with (
            patch.dict(
                os.environ, {"DEEPSEEK_API_KEY": "", "OPENROUTESERVICE_API_KEY": ""}
            ),
            TestClient(create_app()) as client,
        ):
            r = client.get("/api/status")
            self.assertEqual(r.status_code, 200)
            self.assertGreaterEqual(r.json()["tool_count"], 18)
            self.assertEqual(
                client.get("/static/vendor/leaflet/leaflet.js").status_code, 200
            )
            for name, args in [
                ("search_travel_knowledge", {"query": "黄埔"}),
                ("resolve_outing_request", {"question": "香港理工吃什么"}),
                ("get_route", {"origin": "a", "destination": "b"}),
            ]:
                self.assertEqual(
                    client.post(
                        "/api/query", json={"tool": name, "arguments": args}
                    ).status_code,
                    200,
                )

    def test_streaming_progress_evidence_tokens(self):
        from starlette.testclient import TestClient
        from web_app import create_app

        async def fake_answer(*args):
            notes = args[-1]
            i = notes.begin("正在查找附近美食")
            notes.evidence({"ok": True, "data": []})
            notes.token("Hi")
            notes.end(i)
            return "Hi"

        with (
            patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}),
            TestClient(create_app()) as client,
            patch("web_app.prepare_question", return_value=(["food"], "question")),
            patch("web_app.answer", side_effect=fake_answer),
        ):
            client.app.state.llm = object()
            response = client.post(
                "/api/chat", json={"session_id": "test-session-123", "message": "food"}
            )
            events = [json.loads(x) for x in response.text.splitlines()]
            for kind in ["step", "token", "evidence", "done"]:
                self.assertIn(kind, [e["type"] for e in events])
            self.assertEqual(events[-1]["type"], "done")


class OverviewTests(unittest.TestCase):
    def test_selected_sources_and_partial_results(self):
        from web_app import run_tool

        with (
            patch("web_app._weather", return_value={"ok": True, "text": "forecast"}),
            patch(
                "web_app._food",
                return_value={"ok": False, "error": {"message": "unavailable"}},
            ),
            patch("web_app._attractions") as attractions,
        ):
            result = run_tool(
                "get_outing_overview",
                {"location": "Polyu", "include_attractions": False},
            )
            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["data"]["weather"]["text"], "forecast")
            attractions.assert_not_called()

    def test_all_sources_failed_is_error(self):
        from web_app import run_tool

        with (
            patch("web_app._weather", return_value={"ok": False}),
            patch("web_app._food", return_value={"ok": False}),
        ):
            result = run_tool("get_outing_overview", {"location": "Polyu"})
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "error")
