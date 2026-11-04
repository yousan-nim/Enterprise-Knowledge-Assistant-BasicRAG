import psycopg
from pathlib import Path
import httpx
from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from starlette.concurrency import run_in_threadpool

from app.api_docs.api_docs import (
    DOCUMENT_ERRORS, DOCUMENT_LIST_ERRORS, DOCUMENT_DELETE_ERRORS,
    DocumentResponse, DocumentSummary,
)
from app.services.ingestion import ingest_pages
from app.services.parsing import DocumentParseError, parse_document

from app.storage.postgres import get_documents, delete_document

router = APIRouter()


MAX_UPLOAD_BYTES = 1024 * 1024


@router.post("/documents",
    status_code=201,
    response_model=DocumentResponse,
    tags=["Documents"],
    summary="Upload and index a TXT, Markdown or PDF document",
    description="Send multipart/form-data with a file field. Accepts UTF-8 TXT/Markdown (including BOM) and text-based PDF, at most 1 MiB, 50 PDF pages and 50,000 extracted characters. Rejects empty text, null characters, damaged and encrypted PDFs. Scanned PDFs require OCR, which is not supported. Completes embeddings before atomically replacing the previous document in PostgreSQL. The uploaded binary is not retained.",
    responses=DOCUMENT_ERRORS)
async def prepare_document(
    file: UploadFile = File(
        ...,
        description="A .txt, .md or text-based .pdf file.",
    ),
):
    try:
        filename = (
            (file.filename or "")
            .replace("\\", "/")
            .split("/")[-1]
        )

        if Path(filename).suffix.lower() not in {".txt", ".md", ".pdf"}:
            raise HTTPException(
                status_code=415,
                detail="Upload a .txt, .md or .pdf file.",
            )

        data = await file.read(MAX_UPLOAD_BYTES + 1)

        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="The file must be 1 MiB or smaller.",
            )

        try:
            pages = await run_in_threadpool(
                parse_document,
                data,
                filename,
            )
        except DocumentParseError as error:
            raise HTTPException(
                status_code=422,
                detail=str(error),
            )

        try:
            return await ingest_pages(
                pages,
                source=filename[:150],
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Embedding took too long.",
            )
        except httpx.HTTPError:
            raise HTTPException(
                status_code=503,
                detail="Cannot call Ollama. Check the embedding model.",
            )
        except ValueError:
            raise HTTPException(
                status_code=502,
                detail="The extracted text or embeddings are invalid.",
            )
        except (psycopg.Error, OSError):
            raise HTTPException(
                status_code=503,
                detail="Cannot save the document. Please try again.",
            )

    finally:
        await file.close()


@router.get(
    "/documents",
    response_model=list[DocumentSummary],
    tags=["Documents"],
    summary="List indexed documents",
    responses=DOCUMENT_LIST_ERRORS,
)
def list_documents():
    try:
        return get_documents()
    except (psycopg.Error, OSError) as error:
        raise HTTPException(
            status_code=503,
            detail="Cannot read documents from PostgreSQL.",
        ) from error


@router.delete(
    "/documents/{document_id}",
    status_code=204,
    response_class=Response,
    tags=["Documents"],
    summary="Delete a document and its chunks",
    responses=DOCUMENT_DELETE_ERRORS,
)
def remove_document(document_id: str):
    try:
        deleted = delete_document(document_id)
    except (psycopg.Error, OSError) as error:
        raise HTTPException(
            status_code=503,
            detail="Cannot delete the document from PostgreSQL.",
        ) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return Response(status_code=204)
