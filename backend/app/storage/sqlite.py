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
        (document_id, chunk["id"], position, chunk["text"], json.dumps(chunk["embedding"], allow_nan=False))
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
                "INSERT INTO chunks (document_id, id, position, text, embedding) VALUES (?, ?, ?, ?, ?)",
                rows,
            )
    finally:
        connection.close()


def get_chunks() -> list[dict]:
    connection = connect()
    try:
        rows = connection.execute("""
            SELECT c.id, c.document_id, c.text, c.embedding, d.source, d.embedding_model
            FROM chunks c JOIN documents d ON d.id = c.document_id
            ORDER BY c.position
        """).fetchall()
    finally:
        connection.close()
    if any(row["embedding_model"] != EMBED_MODEL for row in rows):
        raise ValueError("The embedding model changed. Upload the document again.")
    return [
        {"id": row["id"], "document_id": row["document_id"], "text": row["text"],
         "source": row["source"], "embedding": json.loads(row["embedding"])}
        for row in rows
    ]
