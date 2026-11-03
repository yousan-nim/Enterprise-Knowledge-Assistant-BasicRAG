import json
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path
import httpx
from app.main import app
from app.storage.sqlite import get_chunks, replace_chunks

OriginalClient = httpx.AsyncClient

class RagApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.setup_database()

    def setup_database(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch('app.storage.sqlite.DATA_DIR', Path(directory.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        pass

    async def test_prepare_then_question_returns_answer_and_sources(self):
        def handler(request):
            payload = json.loads(request.content)
            if request.url.path == '/api/embed':
                return httpx.Response(200, json={'embeddings': [[1., 0.] for _ in payload['input']]})
            prompt = payload['messages'][0]['content']
            self.assertIn('ค่ารถ', prompt)
            self.assertIn('THB 500 per day', prompt)
            self.assertIn('format', payload)
            return httpx.Response(200, json={'message': {'content': json.dumps({'answer': '500 บาทต่อวัน', 'citation_ids': ['chunk-2']})}})
        async with OriginalClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            with patch('app.services.ollama.httpx.AsyncClient', side_effect=lambda **kw: OriginalClient(transport=httpx.MockTransport(handler), **kw)):
                prepared = await client.post('/api/v1/documents', files={'file': ('handbook.md', (Path(__file__).resolve().parents[2] / 'samples/company-handbook.md').read_bytes(), 'text/markdown')})
                response = await client.post('/api/v1/questions', json={'question': 'ค่ารถเบิกได้เท่าไร', 'top_k': 2})
        self.assertEqual(prepared.status_code, 201)
        self.assertEqual(prepared.json()['chunks'], 2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['answer'], '500 บาทต่อวัน')
        self.assertTrue(response.json()['found'])
        self.assertEqual(response.json()['citation_ids'], ['chunk-2'])
        self.assertEqual(len(response.json()['sources']), 2)

    async def test_question_before_ingestion_returns_conflict(self):
        async with OriginalClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            response = await client.post('/api/v1/questions', json={'question': 'test'})
        self.assertEqual(response.status_code, 409)

    async def test_failed_ingestion_preserves_previous_chunks(self):
        existing = [{'id': 'old', 'document_id': 'old-doc', 'text': 'old', 'source': 'old.md', 'embedding': [1., 0.]}]
        replace_chunks(existing)
        def handler(request):
            raise httpx.ConnectError('unavailable')
        async with OriginalClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            with patch('app.services.ollama.httpx.AsyncClient', side_effect=lambda **kw: OriginalClient(transport=httpx.MockTransport(handler), **kw)):
                response = await client.post('/api/v1/documents', files={'file': ('handbook.md', (Path(__file__).resolve().parents[2] / 'samples/company-handbook.md').read_bytes(), 'text/markdown')})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(get_chunks(), existing)

    def test_memory_getter_does_not_expose_list(self):
        replace_chunks([{'id':'old','document_id':'old-doc','text':'old','source':'old.md','embedding':[1.,0.]}])
        returned = get_chunks()
        returned.clear()
        self.assertEqual(len(get_chunks()), 1)
