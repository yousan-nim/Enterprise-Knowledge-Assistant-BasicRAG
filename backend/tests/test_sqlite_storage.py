import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from app.storage import sqlite as storage


class SqliteStorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)
        patcher = patch('app.storage.sqlite.DATA_DIR', self.path)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.chunks = [{'document_id':'doc-1','id':'chunk-1','source':'demo.md',
                        'text':'Sample evidence','embedding':[1.,0.]}]

    def test_new_process_reads_persisted_vectors(self):
        storage.replace_chunks(self.chunks)
        backend = Path(__file__).resolve().parents[1]
        env = {**os.environ, 'RAG_DATA_DIR':str(self.path), 'PYTHONPATH':str(backend), 'PYTHONDONTWRITEBYTECODE':'1'}
        result = subprocess.run([sys.executable,'-c','import json; from app.storage.sqlite import get_chunks; print(json.dumps(get_chunks()))'],
                                cwd=backend, env=env, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout),self.chunks)

    def test_transaction_failure_restores_old_document(self):
        storage.replace_chunks(self.chunks)
        duplicate = {'document_id':'doc-2','id':'same','source':'new.md','text':'new','embedding':[0.,1.]}
        with self.assertRaises(sqlite3.IntegrityError):
            storage.replace_chunks([duplicate,duplicate])
        self.assertEqual(storage.get_chunks(),self.chunks)

    def test_replacement_removes_old_chunks(self):
        storage.replace_chunks(self.chunks)
        new = [{'document_id':'doc-2','id':'chunk-2','source':'new.md','text':'new','embedding':[0.,1.]}]
        storage.replace_chunks(new)
        self.assertEqual(storage.get_chunks(),new)

    def test_model_change_requires_reindexing(self):
        storage.replace_chunks(self.chunks)
        with patch('app.storage.sqlite.EMBED_MODEL','different-model'):
            with self.assertRaisesRegex(ValueError,'model changed'):
                storage.get_chunks()
