import unittest
from unittest.mock import patch

import httpx

from app.services import ollama

OriginalClient = httpx.AsyncClient


class OllamaEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_embedding_and_chat_use_configured_endpoint(self):
        paths = []

        def handler(request):
            self.assertEqual(request.url.host, 'ollama')
            paths.append(request.url.path)
            if request.url.path == '/api/embed':
                return httpx.Response(200, json={'embeddings': [[1., 0.]]})
            return httpx.Response(200, json={'message': {'content': 'hello'}})

        with patch.object(ollama, 'OLLAMA_BASE_URL', 'http://ollama:11434'):
            with patch.object(ollama.httpx, 'AsyncClient', side_effect=lambda **kw: OriginalClient(transport=httpx.MockTransport(handler), **kw)):
                self.assertEqual(await ollama.embed_texts(['test']), [[1., 0.]])
                self.assertEqual(await ollama.generate_answer('test'), 'hello')
        self.assertEqual(paths, ['/api/embed', '/api/chat'])
