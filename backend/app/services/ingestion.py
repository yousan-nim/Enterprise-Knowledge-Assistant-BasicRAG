from pathlib import Path
from uuid import uuid4

from app.services.chunking import chunk_text
from app.services.ollama import embed_texts
from app.storage.sqlite import replace_chunks


async def ingest_text(text: str, source: str) -> dict:
    texts = chunk_text(text, chunk_size=250, overlap=50)
    
    if not texts: 
        raise ValueError("The document contains no text.")
    
    vectors = await embed_texts(texts)
    document_id = str(uuid4())
    
    chunks = [
        {
            "id": f"chunk-{index}",
        "document_id": document_id, 
        "text" : chunk,
        "source": source,
        "embedding": vector,
        }
        
        for index, (chunk, vector) in enumerate(zip(texts, vectors), start=1)
    ]
    
    replace_chunks(chunks)
    
    return {
        "document_id": document_id,
        "source": source,
        "chunks": len(chunks),
    }
    

async def ingest_document(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return await ingest_text(text, source=path.name)
