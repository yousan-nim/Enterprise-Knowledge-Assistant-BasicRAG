from storage_double import use_storage_double
import psycopg
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app.main import app
from app.storage import sqlite as storage


class DocumentManagementTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        use_storage_double(self)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch('app.storage.sqlite.DATA_DIR', Path(directory.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_list_delete_and_question_after_delete(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            self.assertEqual((await client.get('/api/v1/documents')).json(), [])
            storage.replace_chunks([{
                'document_id': 'doc-1', 'id': 'chunk-1', 'source': 'demo.pdf',
                'text': 'Evidence', 'embedding': [1., 0.],
            }])
            response = await client.get('/api/v1/documents')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [{
                'document_id': 'doc-1', 'source': 'demo.pdf',
                'embedding_model': storage.EMBED_MODEL, 'chunks': 1,
            }])
            response = await client.delete('/api/v1/documents/missing')
            self.assertEqual(response.status_code, 404)
            self.assertEqual(len(storage.get_chunks()), 1)
            response = await client.delete('/api/v1/documents/doc-1')
            self.assertEqual(response.status_code, 204)
            self.assertEqual(response.content, b'')
            self.assertEqual(storage.get_chunks(), [])
            self.assertEqual((await client.get('/api/v1/documents')).json(), [])
            self.assertEqual((await client.delete('/api/v1/documents/doc-1')).status_code, 404)
            response = await client.post('/api/v1/questions', json={'question': 'What does it say?'})
            self.assertEqual(response.status_code, 409)

    async def test_storage_errors_return_503(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            with patch('app.routes.documents.get_documents', side_effect=psycopg.OperationalError('private database path')):
                response = await client.get('/api/v1/documents')
                self.assertEqual(response.status_code, 503)
                self.assertNotIn('private', response.text)
            with patch('app.routes.documents.delete_document', side_effect=OSError('private database path')):
                response = await client.delete('/api/v1/documents/doc-1')
                self.assertEqual(response.status_code, 503)
                self.assertNotIn('private', response.text)
