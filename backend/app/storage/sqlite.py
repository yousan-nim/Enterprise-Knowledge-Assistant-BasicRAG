import json
import sqlite3

from app.config.config import DATA_DIR, EMBED_MODEL


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATA_DIR / "knowledge.db", timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                embedding_model TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chunks (
                document_id TEXT NOT NULL,
                id TEXT NOT NULL,
                position INTEGER NOT NULL,
                text TEXT NOT NULL,
                embedding TEXT NOT NULL,
                PRIMARY KEY (document_id, id),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
        """)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(chunks)")}
        with connection:
            if "page" not in columns:
                connection.execute("ALTER TABLE chunks ADD COLUMN page INTEGER NOT NULL DEFAULT 1")
            if "extraction_method" not in columns:
                connection.execute("ALTER TABLE chunks ADD COLUMN extraction_method TEXT NOT NULL DEFAULT 'direct'")
    except Exception:
        connection.close()
        raise
    return connection


def replace_chunks(chunks: list[dict]) -> None:
    if not chunks:
        raise ValueError("Chunks list cannot be empty.")
    document_id = chunks[0]["document_id"]
    source = chunks[0]["source"]
    if any(chunk["document_id"] != document_id or chunk["source"] != source for chunk in chunks):
        raise ValueError("All chunks must belong to the same document and source.")
    rows = [
        (document_id, chunk["id"], position, chunk["text"], json.dumps(chunk["embedding"], allow_nan=False),
         chunk.get("page", 1), chunk.get("extraction_method", "direct"))
        for position, chunk in enumerate(chunks)
    ]
    connection = connect()
    try:
        with connection:
            connection.execute("DELETE FROM documents")
            connection.execute(
                "INSERT INTO documents (id, source, embedding_model) VALUES (?, ?, ?)",
                (document_id, source, EMBED_MODEL),
            )
            connection.executemany(
                "INSERT INTO chunks (document_id, id, position, text, embedding, page, extraction_method) VALUES (?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
    finally:
        connection.close()


def get_chunks() -> list[dict]:
    connection = connect()
    try:
        rows = connection.execute("""
            SELECT c.id, c.document_id, c.text, c.embedding, c.page, c.extraction_method, d.source, d.embedding_model
            FROM chunks c JOIN documents d ON d.id = c.document_id
            ORDER BY c.position
        """).fetchall()
    finally:
        connection.close()
    if any(row["embedding_model"] != EMBED_MODEL for row in rows):
        raise ValueError("The embedding model changed. Upload the document again.")
    return [
        {"id": row["id"], "document_id": row["document_id"], "text": row["text"],
         "source": row["source"], "embedding": json.loads(row["embedding"]),
         "page": row["page"], "extraction_method": row["extraction_method"]}
        for row in rows
    ]


def get_documents() -> list[dict]:
    connection = connect()
    try:
        rows = connection.execute("""
            SELECT d.id AS document_id, d.source, d.embedding_model,
                   COUNT(c.id) AS chunks
            FROM documents AS d
            LEFT JOIN chunks AS c ON c.document_id = d.id
            GROUP BY d.id, d.source, d.embedding_model
            ORDER BY d.id
        """).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def delete_document(document_id: str) -> bool:
    connection = connect()
    try:
        with connection:
            cursor = connection.execute(
                "DELETE FROM documents WHERE id = ?",
                (document_id,),
            )
            return cursor.rowcount > 0
    finally:
        connection.close()
