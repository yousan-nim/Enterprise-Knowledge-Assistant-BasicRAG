import sqlite3
from pathlib import Path
import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from app.api_docs.api_docs import DOCUMENT_ERRORS, DocumentResponse
from app.services.ingestion import ingest_text

router = APIRouter()


MAX_UPLOAD_BYTES = 1024 * 1024
MAX_TEXT_CHARACTERS = 50_000


@router.post("/documents", status_code=201, response_model=DocumentResponse,
          tags=["Documents"], summary="Upload and index a TXT or Markdown document",
          description="Send multipart/form-data with a file field. Accepts UTF-8 (including BOM), at most 1 MiB and 50,000 characters. Rejects empty text and null characters. Builds embeddings synchronously, then atomically replaces the previous document in SQLite. No PDF/OCR support. The uploaded binary is not retained.",
          responses=DOCUMENT_ERRORS)
async def prepare_document(file: UploadFile = File(..., description="UTF-8 .txt or .md file. Successful indexing replaces the current document.")):
    try:
        filename = (file.filename or "").replace("\\", "/").split("/")[-1]
        if Path(filename).suffix.lower() not in {".txt", ".md"}:
            raise HTTPException(415, "Upload a .txt or .md file.")

        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "The file must be 1 MiB or smaller.")

        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(422, "The file must contain UTF-8 text.")

        if not text.strip():
            raise HTTPException(422, "The file contains no text.")
        if "\x00" in text:
            raise HTTPException(422, "The file contains unsupported null characters.")
        if len(text) > MAX_TEXT_CHARACTERS:
            raise HTTPException(413, "The document must contain at most 50,000 characters.")

        try:
            return await ingest_text(text, source=filename[:150])
        except httpx.TimeoutException:
            raise HTTPException(504, "Embedding took too long.")
        except httpx.HTTPError:
            raise HTTPException(503, "Cannot call Ollama. Check the embedding model.")
        except ValueError:
            raise HTTPException(502, "Ollama returned invalid embeddings.")
        except (sqlite3.Error, OSError):
            raise HTTPException(503, "Cannot save the document. Please try again.")
    finally:
        await file.close()
