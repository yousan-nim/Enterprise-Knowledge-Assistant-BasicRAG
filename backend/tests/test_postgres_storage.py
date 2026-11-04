import os
from pathlib import Path
from uuid import uuid4
import unittest
from unittest.mock import patch

import psycopg
from psycopg import sql

from app.storage import postgres


def make_chunk(document_id=None, **overrides):
    return {
        'document_id': document_id or str(uuid4()), 'id': 'chunk-1',
        'source': 'demo.pdf', 'text': 'Evidence',
        'embedding': [1.] + [0.] * 767, 'page': 2,
        'extraction_method': 'direct', **overrides,
    }


class PostgresValidationTests(unittest.TestCase):
    def test_invalid_input_fails_before_connecting(self):
        chunk = make_chunk()
        cases = [[], [make_chunk(embedding=[1., 0.])],
                 [make_chunk(embedding=[0.] * 768)],
                 [make_chunk(embedding=[float('nan')] + [0.] * 767)],
                 [make_chunk(embedding=[True] + [0.] * 767)],
                 [chunk, make_chunk(chunk['document_id'], source='other.pdf')],
                 [chunk, make_chunk()]]
        with patch.object(postgres, 'connect') as connect:
            for chunks in cases:
                with self.subTest(chunks=len(chunks)):
                    with self.assertRaises(ValueError):
                        postgres.replace_chunks(chunks)
            connect.assert_not_called()


    def test_invalid_search_input_fails_before_connecting(self):
        vector = [1.] + [0.] * 767
        cases = [([1., 0.], 3), ([0.] * 768, 3),
                 ([float('inf')] + [0.] * 767, 3),
                 ([True] + [0.] * 767, 3),
                 (vector, 0), (vector, 11), (vector, True)]
        with patch.object(postgres, 'connect') as connect:
            for query, top_k in cases:
                with self.subTest(top_k=top_k):
                    with self.assertRaises(ValueError):
                        postgres.search_chunks(query, top_k)
            connect.assert_not_called()

    def test_invalid_delete_id_does_not_connect(self):
        with patch.object(postgres, 'connect') as connect:
            for document_id in ['', 'not-a-uuid', "id' OR 1=1 --"]:
                with self.subTest(document_id=document_id):
                    self.assertFalse(postgres.delete_document(document_id))
            connect.assert_not_called()


@unittest.skipUnless(os.getenv('RUN_POSTGRES_TESTS') == '1', 'Set RUN_POSTGRES_TESTS=1 for real PostgreSQL tests')
class PostgresStorageIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.real_connect = postgres.connect
        self.schema = 'test_rag_' + uuid4().hex
        with self.real_connect() as connection:
            connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.schema)))
        self.addCleanup(self.drop_schema)
        with self.scoped_connect() as connection:
            schema_path = Path(__file__).resolve().parents[2] / 'infra/postgres/schema.sql'
            schema_sql = schema_path.read_text().replace('BEGIN;', '').replace('COMMIT;', '')
            connection.execute(schema_sql)
        patcher = patch.object(postgres, 'connect', self.scoped_connect)
        patcher.start()
        self.addCleanup(patcher.stop)

    def scoped_connect(self):
        connection = self.real_connect()
        connection.execute("SELECT set_config('search_path', %s, false)", (self.schema + ',public',))
        connection.commit()
        return connection

    def drop_schema(self):
        with self.real_connect() as connection:
            connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(self.schema)))

    def test_replacement_persists_vectors_and_metadata(self):
        postgres.replace_chunks([make_chunk()])
        chunk = make_chunk(page=3, extraction_method='ocr')
        postgres.replace_chunks([chunk])
        self.assertEqual(postgres.get_documents(), [{
            'document_id': chunk['document_id'], 'source': 'demo.pdf',
            'embedding_model': postgres.EMBED_MODEL, 'chunks': 1,
        }])
        with postgres.connect() as connection:
            row = connection.execute('SELECT document_id::text, page, extraction_method, position, vector_dims(embedding) AS dimensions, embedding::text FROM chunks').fetchone()
        import json
        self.assertEqual(json.loads(row['embedding']), chunk['embedding'])
        self.assertEqual(row['document_id'], chunk['document_id'])
        self.assertEqual((row['page'], row['extraction_method'], row['position'], row['dimensions']), (3, 'ocr', 0, 768))

    def test_duplicate_chunk_rolls_back_replacement(self):
        old = make_chunk()
        postgres.replace_chunks([old])
        new = make_chunk()
        with self.assertRaises(psycopg.IntegrityError):
            postgres.replace_chunks([new, new])
        self.assertEqual(postgres.get_documents()[0]['document_id'], old['document_id'])
        with postgres.connect() as connection:
            row = connection.execute('SELECT text, page, COUNT(*) OVER () AS total FROM chunks').fetchone()
        self.assertEqual((row['text'], row['page'], row['total']), ('Evidence', 2, 1))

    def test_invalid_page_rolls_back_replacement(self):
        old = make_chunk()
        postgres.replace_chunks([old])
        with self.assertRaises(psycopg.IntegrityError):
            postgres.replace_chunks([make_chunk(page=0)])
        self.assertEqual(postgres.get_documents()[0]['document_id'], old['document_id'])


    def test_search_orders_scores_and_keeps_metadata(self):
        first = make_chunk()
        second = make_chunk(first['document_id'], id='chunk-2', page=3, embedding=[0., 1.] + [0.] * 766)
        third = make_chunk(first['document_id'], id='chunk-3', page=4, embedding=[-1.] + [0.] * 767)
        postgres.replace_chunks([first, second, third])
        results = postgres.search_chunks(first['embedding'], top_k=3)
        self.assertEqual([row['id'] for row in results], ['chunk-1', 'chunk-2', 'chunk-3'])
        for row, expected in zip(results, [1., 0., -1.]):
            self.assertAlmostEqual(row['score'], expected)
        self.assertEqual(results[1]['page'], 3)
        self.assertEqual(results[0]['source'], 'demo.pdf')
        self.assertEqual(results[0]['document_id'], first['document_id'])
        self.assertEqual(len(postgres.search_chunks(first['embedding'], top_k=1)), 1)

    def test_search_empty_and_changed_model(self):
        chunk = make_chunk()
        self.assertEqual(postgres.search_chunks(chunk['embedding']), [])
        postgres.replace_chunks([chunk])
        with patch.object(postgres, 'EMBED_MODEL', 'different-model'):
            with self.assertRaisesRegex(ValueError, 'model changed'):
                postgres.search_chunks(chunk['embedding'])

    def test_search_breaks_ties_by_position(self):
        first = make_chunk(id='chunk-z')
        second = make_chunk(first['document_id'], id='chunk-a')
        postgres.replace_chunks([first, second])
        self.assertEqual([row['id'] for row in postgres.search_chunks(first['embedding'])], ['chunk-z', 'chunk-a'])


    def test_delete_cascades_and_persists(self):
        chunk = make_chunk()
        postgres.replace_chunks([chunk])
        self.assertTrue(postgres.delete_document(chunk['document_id']))
        self.assertEqual(postgres.get_documents(), [])
        with postgres.connect() as connection:
            count = connection.execute('SELECT COUNT(*) AS total FROM chunks').fetchone()['total']
        self.assertEqual(count, 0)
        self.assertFalse(postgres.delete_document(chunk['document_id']))

    def test_delete_unknown_uuid_preserves_document(self):
        chunk = make_chunk()
        postgres.replace_chunks([chunk])
        self.assertFalse(postgres.delete_document(str(uuid4())))
        self.assertEqual(postgres.get_documents()[0]['document_id'], chunk['document_id'])
        self.assertEqual(len(postgres.search_chunks(chunk['embedding'])), 1)
