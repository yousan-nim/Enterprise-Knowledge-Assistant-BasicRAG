import unittest
from unittest.mock import AsyncMock, patch
import httpx
from app.services.generation import answer_with_sources

class StructuredRetryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.results = [{'id':'chunk-2','source':'handbook.md','text':'Travel expenses are limited to 500 baht per day.'}]
        self.valid = '{"answer":"500 บาทต่อวัน","citation_ids":["chunk-2"]}'

    async def test_retries_invalid_response(self):
        invalid = '{"answer":"ไม่พบข้อมูลในเอกสาร","citation_ids":["chunk-2"]}'
        with patch('app.services.generation.generate_answer', new_callable=AsyncMock, side_effect=[invalid,self.valid]) as model:
            answer = await answer_with_sources('ค่าเดินทาง?',self.results)
        self.assertTrue(answer.found)
        self.assertEqual(model.await_count,2)
        self.assertIn('Validation errors:',model.call_args_list[1].args[0])
        self.assertIn(self.results[0]['text'],model.call_args_list[1].args[0])

    async def test_stops_after_two_unknown_citations(self):
        invalid = '{"answer":"500","citation_ids":["chunk-99"]}'
        with patch('app.services.generation.generate_answer', new_callable=AsyncMock, return_value=invalid) as model:
            with self.assertRaisesRegex(ValueError,'after 2 attempts'):
                await answer_with_sources('ค่าเดินทาง?',self.results)
        self.assertEqual(model.await_count,2)

    async def test_valid_does_not_retry(self):
        with patch('app.services.generation.generate_answer', new_callable=AsyncMock, return_value=self.valid) as model:
            await answer_with_sources('ค่าเดินทาง?',self.results)
        self.assertEqual(model.await_count,1)

    async def test_malformed_json_is_retried(self):
        with patch('app.services.generation.generate_answer', new_callable=AsyncMock, side_effect=['not json',self.valid]) as model:
            await answer_with_sources('ค่าเดินทาง?',self.results)
        self.assertEqual(model.await_count,2)

    async def test_transport_failure_is_not_retried(self):
        with patch('app.services.generation.generate_answer', new_callable=AsyncMock, side_effect=httpx.ConnectError('unavailable')) as model:
            with self.assertRaises(httpx.ConnectError):
                await answer_with_sources('ค่าเดินทาง?',self.results)
        self.assertEqual(model.await_count,1)
