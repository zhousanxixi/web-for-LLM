import asyncio
import json
import os
import time
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from chat import classify_question, prepare_question, recent_context, tools_for
from places_rag import rank_candidates
from mcp_servers import weather_server as weather


class ConversationTests(unittest.TestCase):
    def model(self, payload):
        client = Mock()
        client.chat.completions.create.return_value = NS(choices=[NS(message=NS(content=json.dumps(payload)))])
        return client

    def test_followup_uses_bounded_history_and_configured_model(self):
        client = self.model({'type': ['outing'], 'place': '尖沙咀'})
        history = [{'role': 'system', 'content': 'secret instructions'},
                   {'role': 'user', 'content': 'RETRIEVAL PAYLOAD\n用户问题：尖沙咀有什么景点'},
                   {'role': 'assistant', 'content': '附近可去科学馆。'},
                   {'role': 'tool', 'content': 'large tool payload'}]
        with patch.dict(os.environ, {'LLM_MODEL': 'custom-chat'}):
            self.assertEqual(classify_question(client, '那里有室内的吗', history), (['outing'], '尖沙咀'))
        args = client.chat.completions.create.call_args.kwargs
        self.assertEqual(args['model'], 'custom-chat')
        self.assertEqual(args['timeout'], 12)
        self.assertEqual(args['messages'][1]['content'], '尖沙咀有什么景点')
        self.assertNotIn('RETRIEVAL PAYLOAD', json.dumps(args))
        self.assertNotIn('large tool payload', json.dumps(args))
        self.assertEqual(args['messages'][-1]['content'], '那里有室内的吗')

    def test_invalid_json_does_not_default_to_weather(self):
        client = self.model({})
        client.chat.completions.create.return_value.choices[0].message.content = 'not json'
        self.assertEqual(classify_question(client, '你好'), ([], None))
        self.assertEqual(tools_for([], [{'function': {'name': 'get_weather_info'}}]), [])

    def test_provider_failure_preserves_clear_intent(self):
        client = Mock()
        client.chat.completions.create.side_effect = RuntimeError('provider failed')
        self.assertEqual(classify_question(client, '香港理工有什么好吃的'), (['food'], '香港理工大学'))

    def test_ambiguous_followup_has_no_guessed_destination(self):
        client = self.model({'type': ['outing'], 'place': None})
        self.assertEqual(classify_question(client, '那里有什么', [{'role': 'assistant', 'content': '中环或旺角都可以'}]), (['outing'], None))

    def test_prepare_forwards_history_without_mutating_it(self):
        client = self.model({'type': ['food'], 'place': None})
        history = [{'role': 'user', 'content': '我在尖沙咀'}]
        with patch('chat.place_context') as lookup:
            self.assertEqual(prepare_question(client, '附近吃什么', history=history), (['food'], '附近吃什么'))
        lookup.assert_not_called()
        self.assertEqual(history, [{'role': 'user', 'content': '我在尖沙咀'}])
        self.assertEqual(len(recent_context(history * 10)), 6)


class CandidateTests(unittest.TestCase):
    def test_explicit_indoor_evidence_ranks_above_nearer_unknown(self):
        rows = [{'id': 'park', 'text': '公园有步道。', 'distance_km': .1},
                {'id': 'museum', 'text': '设有室内展览。', 'distance_km': .5}]
        result = rank_candidates(rows, '雨天去哪里')
        self.assertEqual([r['id'] for r in result], ['museum', 'park'])
        self.assertEqual(result[1]['suitability'][0]['status'], 'unknown')
        self.assertEqual(result[0]['suitability'][0]['evidence'], '设有室内展览。')
        self.assertNotIn('suitability', rows[0])

    def test_explicit_accessibility_negative_excluded(self):
        result = rank_candidates([{'text': 'Not wheelchair accessible.'}, {'text': '设施情况未确认。'}], 'wheelchair')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['suitability'][0]['status'], 'unknown')

    def test_no_conditions_preserves_distance_order(self):
        rows = [{'id': 'a'}, {'id': 'b'}]
        self.assertEqual(rank_candidates(rows, '附近景点'), rows)


class StationTests(unittest.TestCase):
    def query(self, rows):
        stations = [{'name': 'Nearest', 'latitude': 22.3, 'longitude': 114.1},
                    {'name': 'Available', 'latitude': 22.31, 'longitude': 114.1}]
        with patch.object(weather, 'geocode_place', return_value={'name': 'place', 'latitude': 22.3, 'longitude': 114.1}), \
             patch.object(weather, 'load_stations', return_value=stations), \
             patch.object(weather, 'fetch_text', return_value='fixture'), \
             patch.object(weather, 'latest_temperatures', return_value=rows):
            return weather.get_nearest_temperature('place')

    def row(self, name, value):
        return {'Automatic Weather Station': name, 'Air Temperature(degree Celsius)': value, 'Date time': '2026-11-12 12:00'}

    def test_missing_or_invalid_nearest_uses_available_station(self):
        text = self.query([self.row('Nearest', 'N/A'), self.row('Available', '24')])
        self.assertIn('最近站 Nearest 暂无有效观测', text)
        self.assertIn('Available: 24°C', text)
        self.assertIn('2026-11-12 12:00', text)
        self.assertIn('距离:', text)

    def test_no_valid_observation_not_fabricated(self):
        for value in ['N/A', '', 'nan', 'inf']:
            self.assertIn('没有可匹配的有效气温观测', self.query([self.row('Nearest', value)]))

    def test_nearest_valid_station_kept(self):
        text = self.query([self.row('Nearest', '23'), self.row('Available', '24')])
        self.assertIn('Nearest: 23°C', text)
        self.assertNotIn('暂无有效观测', text)


class WholeTurnTimeoutTests(unittest.TestCase):
    def test_preparation_is_inside_timeout_and_history_survives(self):
        from starlette.testclient import TestClient
        from web_app import create_app
        timeout = asyncio.timeout
        def slow_prepare(*args):
            time.sleep(.06)
            return ['food'], 'food'
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': ''}), TestClient(create_app()) as client:
            client.app.state.llm = object()
            with patch('web_app.prepare_question', side_effect=slow_prepare), \
                 patch('web_app.asyncio.timeout', side_effect=lambda seconds: timeout(.01)) as budget, \
                 patch('web_app.answer') as answer:
                response = client.post('/api/chat', json={'session_id': 'timeout-test-123', 'message': 'food'})
            events = [json.loads(line) for line in response.text.splitlines()]
            self.assertEqual(events[-1]['type'], 'error')
            self.assertIn('90秒', events[-1]['message'])
            budget.assert_called_once_with(90)
            answer.assert_not_called()
            item = client.app.state.chat_sessions['timeout-test-123']
            self.assertFalse(item['lock'].locked())
            self.assertEqual(len(item['messages']), 1)

if __name__ == '__main__':
    unittest.main()
