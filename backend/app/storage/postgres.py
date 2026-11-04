import json
import math
from pathlib import Path
from uuid import UUID

import psycopg
from dotenv import dotenv_values
from psycopg.rows import dict_row
import os


from app.config.config import EMBED_MODEL


EMBEDDING_DIMENSION = 768
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class EmbeddingModelMismatch(ValueError):
    pass


def connect() -> psycopg.Connection:
    # Environment variables override the local Compose .env file.
    settings = {
        **dotenv_values(PROJECT_ROOT / ".env"),
        **os.environ,
    }

    password = settings.get("POSTGRES_PASSWORD")
    if not password:
        raise ValueError("POSTGRES_PASSWORD is required.")

    return psycopg.connect(
        host=settings.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(settings.get("POSTGRES_PORT", "5433")),
        dbname=settings.get("POSTGRES_DB", "knowledge"),
        user=settings.get("POSTGRES_USER", "rag"),
        password=password,
        connect_timeout=10,
        row_factory=dict_row,
    )


def get_documents() -> list[dict]:
    with connect() as connection:
        return connection.execute("""
            SELECT
                d.id::text AS document_id,
                d.source,
                d.embedding_model,
                COUNT(c.id) AS chunks
            FROM documents AS d
            LEFT JOIN chunks AS c
                ON c.document_id = d.id
            GROUP BY d.id, d.source, d.embedding_model
            ORDER BY d.id
        """).fetchall()


def replace_chunks(chunks: list[dict]) -> None:
    if not chunks:
        raise ValueError("Chunks list cannot be empty.")

    document_id = chunks[0]["document_id"]
    source = chunks[0]["source"]
    rows = []

    for position, chunk in enumerate(chunks):
        if chunk["document_id"] != document_id or chunk["source"] != source:
            raise ValueError("All chunks must belong to the same document and source.")

        vector = chunk["embedding"]
        if not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSION:
            raise ValueError(f"Each embedding must contain {EMBEDDING_DIMENSION} values.")
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in vector):
            raise ValueError("Embedding values must be finite numbers.")
        if not any(vector):
            raise ValueError("Embedding must not be a zero vector.")

        rows.append((
            document_id, chunk["id"], position, chunk["text"],
            json.dumps(vector, allow_nan=False),
            chunk.get("page", 1), chunk.get("extraction_method", "direct"),
        ))

    with connect() as connection:
        connection.execute("DELETE FROM documents")
        connection.execute(
            "INSERT INTO documents (id, source, embedding_model) VALUES (%s, %s, %s)",
            (document_id, source, EMBED_MODEL),
        )
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO chunks (
                    document_id, id, position, text, embedding, page, extraction_method
                ) VALUES (%s, %s, %s, %s, %s::vector, %s, %s)
                """,
                rows,
            )



def search_chunks(
    query_embedding: list[float],
    top_k: int = 3,
) -> list[dict]:
    if type(top_k) is not int or not 1 <= top_k <= 10:
        raise ValueError("top_k must be an integer between 1 and 10.")

    if (
        not isinstance(query_embedding, list)
        or len(query_embedding) != EMBEDDING_DIMENSION
    ):
        raise ValueError(
            f"Query embedding must contain {EMBEDDING_DIMENSION} values."
        )

    if any(
        type(value) not in (int, float)
        or not math.isfinite(value)
        for value in query_embedding
    ):
        raise ValueError("Query embedding values must be finite numbers.")

    if not any(query_embedding):
        raise ValueError("Query embedding must not be a zero vector.")

    vector = json.dumps(query_embedding, allow_nan=False)

    with connect() as connection:
        # Keep model validation and search on the same database snapshot.
        connection.execute(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
        )

        different_model = connection.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM documents
                WHERE embedding_model <> %s
            ) AS found
            """,
            (EMBED_MODEL,),
        ).fetchone()

        if different_model["found"]:
            raise EmbeddingModelMismatch(
                "The embedding model changed. Upload the document again."
            )

        return connection.execute(
            """
            SELECT
                c.id,
                c.document_id::text AS document_id,
                c.text,
                c.page,
                c.extraction_method,
                d.source,
                1 - (c.embedding <=> %s::vector) AS score
            FROM chunks AS c
            JOIN documents AS d
                ON d.id = c.document_id
            ORDER BY
                c.embedding <=> %s::vector,
                c.document_id,
                c.position
            LIMIT %s
            """,
            (vector, vector, top_k),
        ).fetchall()


def delete_document(document_id: str) -> bool:
    try:
        parsed_id = UUID(document_id)
    except ValueError:
        return False

    with connect() as connection:
        cursor = connection.execute(
            "DELETE FROM documents WHERE id = %s",
            (parsed_id,),
        )
        return cursor.rowcount > 0
