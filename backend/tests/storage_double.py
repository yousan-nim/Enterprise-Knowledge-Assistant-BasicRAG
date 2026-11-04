"""SQLite-backed test double for fast API tests; production always uses PostgreSQL."""
from unittest.mock import patch

from app.storage import sqlite
from app.services.retrieval import search_chunks


def use_storage_double(test):
    def search(query_embedding, top_k):
        return search_chunks(query_embedding, sqlite.get_chunks(), top_k)

    for target, replacement in [
        ('app.services.ingestion.replace_chunks', sqlite.replace_chunks),
        ('app.routes.documents.get_documents', sqlite.get_documents),
        ('app.routes.documents.delete_document', sqlite.delete_document),
        ('app.routes.questions.get_documents', sqlite.get_documents),
        ('app.routes.questions.search_chunks', search),
    ]:
        patcher = patch(target, replacement)
        patcher.start()
        test.addCleanup(patcher.stop)
