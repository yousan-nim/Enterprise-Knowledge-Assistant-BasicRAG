import unittest
from unittest.mock import patch
import httpx
from app.services import generation, ollama

OriginalClient = httpx.AsyncClient

class GenerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_invalid_model_content(self):
        for value in [None, '', '   ', ['unexpected'], 123]:
            with self.subTest(value=value):
                def handler(request):
                    return httpx.Response(200, json={'message': {'content': value}})
                with patch('app.services.ollama.httpx.AsyncClient', side_effect=lambda **kw: OriginalClient(transport=httpx.MockTransport(handler), **kw)):
                    with self.assertRaises(ValueError):
                        await ollama.generate_answer('test')
