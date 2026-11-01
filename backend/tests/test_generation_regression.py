import unittest
from unittest.mock import patch
import httpx
from app.services import generation, ollama

OriginalClient = httpx.AsyncClient

class GenerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_questions_passes_handbook_and_question_to_model(self):
        from app.main import app
        def handler(request):
            import json
            prompt = json.loads(request.content)['messages'][0]['content']
            self.assertIn('THB 500 per day', prompt)
            self.assertIn('ค่ารถ', prompt)
            return httpx.Response(200, json={'message': {'content': '  สูงสุด 500 บาท  '}})
        async with OriginalClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            with patch('app.services.ollama.httpx.AsyncClient', side_effect=lambda **kw: OriginalClient(transport=httpx.MockTransport(handler), **kw)):
                response = await client.post('/questions', json={'question': 'ค่ารถเบิกได้เท่าไร'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['answer'], 'สูงสุด 500 บาท')

    async def test_rejects_invalid_model_content(self):
        for value in [None, '', '   ', ['unexpected'], 123]:
            with self.subTest(value=value):
                def handler(request):
                    return httpx.Response(200, json={'message': {'content': value}})
                with patch('app.services.ollama.httpx.AsyncClient', side_effect=lambda **kw: OriginalClient(transport=httpx.MockTransport(handler), **kw)):
                    with self.assertRaises(ValueError):
                        await ollama.generate_answer('test')
