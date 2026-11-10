import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import psycopg

from app.main import app
from app.schemas.schemas import GroundedAnswer
from app.storage import postgres
from test_parsing import make_pdf
import test_postgres_storage as storage_tests


@unittest.skipUnless(os.getenv('RUN_POSTGRES_TESTS') == '1', 'Set RUN_POSTGRES_TESTS=1 for real PostgreSQL tests')
class PostgresApiTests(unittest.IsolatedAsyncioTestCase):
    setUp = storage_tests.PostgresStorageIntegrationTests.setUp
    scoped_connect = storage_tests.PostgresStorageIntegrationTests.scoped_connect
    drop_schema = storage_tests.PostgresStorageIntegrationTests.drop_schema

    async def test_pdf_upload_question_list_delete(self):
        first = [1.] + [0.] * 767
        second = [0., 1.] + [0.] * 766
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            with patch('app.services.ingestion.embed_texts', new_callable=AsyncMock, return_value=[first, second]):
                response = await client.post('/api/v1/documents', files={'file': ('policy.pdf', make_pdf(['First page', 'Second page']), 'application/pdf')})
            self.assertEqual(response.status_code, 201, response.text)
            document_id = response.json()['document_id']
            self.assertEqual(response.json()['chunks'], 2)
            response = await client.get('/api/v1/documents')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()[0]['document_id'], document_id)
            with patch('app.routes.questions.embed_texts', new_callable=AsyncMock, return_value=[second]):
                with patch('app.routes.questions.answer_with_sources', new_callable=AsyncMock, return_value=GroundedAnswer(answer='Second page', citation_ids=['chunk-2'], found=True)) as answer:
                    response = await client.post('/api/v1/questions', json={'question': 'Which page?', 'top_k': 1})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['sources'][0]['page'], 2)
            self.assertEqual(response.json()['sources'][0]['id'], 'chunk-2')
            self.assertAlmostEqual(response.json()['sources'][0]['score'], 1.)
            self.assertEqual(answer.await_args.args[1][0]['text'], 'Second page')
            self.assertEqual((await client.delete('/api/v1/documents/invalid')).status_code, 404)
            response = await client.delete('/api/v1/documents/' + document_id)
            self.assertEqual(response.status_code, 204)
            self.assertEqual(response.content, b'')
            self.assertEqual((await client.get('/api/v1/documents')).json(), [])
            self.assertEqual(postgres.search_chunks(second), [])
            self.assertEqual((await client.post('/api/v1/questions', json={'question': 'Anything?'})).status_code, 409)

    async def test_upload_database_error_preserves_previous_document(self):
        vector = [1.] + [0.] * 767
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            with patch('app.services.ingestion.embed_texts', new_callable=AsyncMock, return_value=[vector]):
                old = await client.post('/api/v1/documents', files={'file': ('old.txt', b'Old evidence')})
            self.assertEqual(old.status_code, 201)
            with patch('app.services.ingestion.embed_texts', new_callable=AsyncMock, return_value=[vector]):
                with patch('app.services.ingestion.replace_chunks', side_effect=psycopg.OperationalError('private database information')):
                    response = await client.post('/api/v1/documents', files={'file': ('new.txt', b'New evidence')})
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('private', response.text)
            self.assertEqual(postgres.get_documents()[0]['document_id'], old.json()['document_id'])

    async def test_question_model_mismatch_and_search_database_error(self):
        vector = [1.] + [0.] * 767
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            with patch('app.services.ingestion.embed_texts', new_callable=AsyncMock, return_value=[vector]):
                response = await client.post('/api/v1/documents', files={'file': ('old.txt', b'Old evidence')})
            self.assertEqual(response.status_code, 201)
            with patch('app.routes.questions.embed_texts', new_callable=AsyncMock, return_value=[vector]):
                with patch.object(postgres, 'EMBED_MODEL', 'different-model'):
                    response = await client.post('/api/v1/questions', json={'question': 'Anything?'})
                self.assertEqual(response.status_code, 409)
                with patch('app.routes.questions.search_chunks', side_effect=psycopg.OperationalError('private database information')):
                    response = await client.post('/api/v1/questions', json={'question': 'Anything?'})
                self.assertEqual(response.status_code, 503)
                self.assertNotIn('private', response.text)

    @unittest.skipUnless(os.getenv('RUN_OCR_TESTS') == '1', 'Requires real OCR tools')
    async def test_scanned_upload_uses_real_ocr_and_pgvector(self):
        from test_ocr_integration import scanned_pdf
        vector = [1.] + [0.] * 767
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            with patch('app.services.ingestion.embed_texts', new_callable=AsyncMock, return_value=[vector]):
                response = await client.post('/api/v1/documents', files={'file': ('scanned.pdf', scanned_pdf('TRAVEL LIMIT 500'), 'application/pdf')})
            self.assertEqual(response.status_code, 201, response.text)
            stored = postgres.search_chunks(vector)
            self.assertEqual(stored[0]['extraction_method'], 'ocr')
            self.assertEqual(stored[0]['page'], 1)
            self.assertIn('500', stored[0]['text'])
            with patch('app.routes.questions.embed_texts', new_callable=AsyncMock, return_value=[vector]):
                with patch('app.routes.questions.answer_with_sources', new_callable=AsyncMock, return_value=GroundedAnswer(answer='500', citation_ids=['chunk-1'], found=True)):
                    response = await client.post('/api/v1/questions', json={'question': 'What is the limit?'})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['sources'][0]['extraction_method'], 'ocr')
            self.assertEqual(response.json()['sources'][0]['page'], 1)

    @unittest.skipUnless(os.getenv('RUN_OCR_TESTS') == '1', 'Requires real OCR tools')
    async def test_thai_scan_keeps_ocr_metadata_in_postgres(self):
        from pathlib import Path
        data = (Path(__file__).resolve().parents[2] / 'samples/ocr/thai-policy-scan.pdf').read_bytes()
        vector = [1.] + [0.] * 767
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            with patch('app.services.ingestion.embed_texts', new_callable=AsyncMock, side_effect=lambda texts: [vector for _ in texts]):
                response = await client.post('/api/v1/documents', files={'file': ('thai-policy-scan.pdf', data, 'application/pdf')})
        self.assertEqual(response.status_code, 201, response.text)
        results = postgres.search_chunks(vector)
        self.assertTrue(results)
        self.assertTrue(all(item['page'] == 1 and item['extraction_method'] == 'ocr' for item in results))
        self.assertIn('500', ''.join(item['text'] for item in results))
