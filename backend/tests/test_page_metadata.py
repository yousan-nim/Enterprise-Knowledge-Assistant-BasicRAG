from storage_double import use_storage_double
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.config.config import EMBED_MODEL
from app.schemas.documents import DocumentPage
from app.schemas.http import RetrievedSource
from app.services.ingestion import ingest_pages
from app.services.retrieval import search_chunks
from app.storage import sqlite as storage


class PageMetadataTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        use_storage_double(self)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name)
        patcher = patch('app.storage.sqlite.DATA_DIR', self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_pages_keep_provenance_through_storage_and_retrieval(self):
        pages = [DocumentPage(page=1, text='First page'),
                 DocumentPage(page=2, text=''),
                 DocumentPage(page=3, text='Third page', extraction_method='ocr')]
        with patch('app.services.ingestion.embed_texts', new_callable=AsyncMock, return_value=[[1.,0.],[0.,1.]]) as embed:
            result = await ingest_pages(pages, 'policy.pdf')
        embed.assert_awaited_once_with(['First page','Third page'])
        self.assertEqual(result['chunks'],2)
        chunks = storage.get_chunks()
        self.assertEqual([c['page'] for c in chunks],[1,3])
        ranked = search_chunks([0.,1.], chunks, top_k=1)
        source = RetrievedSource(**ranked[0])
        self.assertEqual(source.page,3)
        self.assertEqual(source.extraction_method,'ocr')

    async def test_chunking_does_not_cross_page_boundary(self):
        pages = [DocumentPage(page=1,text='A'*300),DocumentPage(page=2,text='B'*300)]
        with patch('app.services.ingestion.embed_texts',new_callable=AsyncMock,return_value=[[1.,0.]]*4):
            await ingest_pages(pages,'demo.pdf')
        for chunk in storage.get_chunks():
            expected = 'A' if chunk['page']==1 else 'B'
            self.assertEqual(set(chunk['text']),{expected})

    def test_migrates_old_schema_without_losing_document(self):
        with sqlite3.connect(self.path/'knowledge.db') as connection:
            connection.executescript('''
                CREATE TABLE documents (id TEXT PRIMARY KEY, source TEXT NOT NULL, embedding_model TEXT NOT NULL);
                CREATE TABLE chunks (document_id TEXT NOT NULL, id TEXT NOT NULL, position INTEGER NOT NULL,
                    text TEXT NOT NULL, embedding TEXT NOT NULL, PRIMARY KEY(document_id,id),
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE);
            ''')
            connection.execute('INSERT INTO documents VALUES (?,?,?)',('old','old.md',EMBED_MODEL))
            connection.execute('INSERT INTO chunks VALUES (?,?,?,?,?)',('old','chunk-1',0,'old text',json.dumps([1.,0.])))
        first = storage.get_chunks()
        second = storage.get_chunks()
        self.assertEqual(first,second)
        self.assertEqual(first[0]['text'],'old text')
        self.assertEqual(first[0]['page'],1)
        self.assertEqual(first[0]['extraction_method'],'direct')
