-- Initial schema for embeddinggemma's 768-dimensional embeddings.
BEGIN;

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    source TEXT NOT NULL CHECK (length(btrim(source)) > 0),
    embedding_model TEXT NOT NULL CHECK (length(btrim(embedding_model)) > 0)
);

CREATE TABLE IF NOT EXISTS chunks (
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    id TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    text TEXT NOT NULL CHECK (length(btrim(text)) > 0),
    embedding vector(768) NOT NULL CHECK (vector_norm(embedding) > 0),
    page INTEGER NOT NULL DEFAULT 1 CHECK (page >= 1),
    extraction_method TEXT NOT NULL DEFAULT 'direct'
        CHECK (extraction_method IN ('direct', 'ocr')),
    PRIMARY KEY (document_id, id),
    UNIQUE (document_id, position)
);

COMMIT;
