from pathlib import Path
from uuid import uuid4

from app.schemas.documents import DocumentPage
from app.services.chunking import chunk_text
from app.services.ollama import embed_texts
from starlette.concurrency import run_in_threadpool
from app.storage.postgres import replace_chunks


async def ingest_pages(pages: list[DocumentPage], source: str) -> dict:
    pieces = [
        {"text": chunk, "page": page.page, "extraction_method": page.extraction_method}
        for page in pages
        for chunk in chunk_text(page.text, chunk_size=250, overlap=50)
    ]
    if not pieces:
        raise ValueError("The document contains no text.")

    vectors = await embed_texts([piece["text"] for piece in pieces])
    document_id = str(uuid4())
    chunks = [
        {"id": f"chunk-{index}", "document_id": document_id, "source": source,
         "embedding": vector, **piece}
        for index, (piece, vector) in enumerate(zip(pieces, vectors), start=1)
    ]
    await run_in_threadpool(replace_chunks, chunks)
    return {"document_id": document_id, "source": source, "chunks": len(chunks)}


async def ingest_text(text: str, source: str) -> dict:
    return await ingest_pages([DocumentPage(page=1, text=text)], source)


async def ingest_document(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return await ingest_text(text, source=path.name)
