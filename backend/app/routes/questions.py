import httpx
import psycopg
from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.api_docs.api_docs import QUESTION_ERRORS, QUESTION_EXAMPLES
from app.schemas.http import QuestionRequest, QuestionResponse, RetrievedSource
from app.services.generation import answer_with_sources
from app.services.ollama import embed_texts
from app.storage.postgres import EmbeddingModelMismatch, get_documents, search_chunks

router = APIRouter()


@router.post(
    "/questions",
    response_model=QuestionResponse,
    tags=["RAG"],
    summary="Ask a question grounded in the indexed document",
    description=(
        "Embeds the question and retrieves PostgreSQL chunks using pgvector cosine distance. "
        "Generates a structured cited answer with at most two model attempts. "
        "Valid citations do not guarantee factual accuracy."
    ),
    responses={**QUESTION_ERRORS, **QUESTION_EXAMPLES},
)
async def ask_document(body: QuestionRequest):
    question = body.question.strip()
    if not question:
        raise HTTPException(422, "Please enter a question.")

    try:
        documents = await run_in_threadpool(get_documents)
    except (psycopg.Error, OSError) as error:
        raise HTTPException(503, "The document database is unavailable.") from error
    if not documents:
        raise HTTPException(409, "Prepare a document with POST /api/v1/documents first.")

    try:
        query_vector = (await embed_texts([question]))[0]
        results = await run_in_threadpool(
            search_chunks, query_embedding=query_vector, top_k=body.top_k,
        )
        if not results:
            raise HTTPException(409, "No indexed chunks remain. Upload the document again.")
        answer = await answer_with_sources(question, results)
    except EmbeddingModelMismatch as error:
        raise HTTPException(409, str(error)) from error
    except (psycopg.Error, OSError) as error:
        raise HTTPException(503, "The document database is unavailable.") from error
    except httpx.TimeoutException as error:
        raise HTTPException(504, "Ollama took too long to respond.") from error
    except httpx.HTTPError as error:
        raise HTTPException(503, "Cannot call Ollama. Check the app and models.") from error
    except (ValueError, KeyError, TypeError, IndexError) as error:
        raise HTTPException(502, "Retrieval or answer validation failed.") from error

    return QuestionResponse(
        **answer.model_dump(),
        sources=[RetrievedSource(**result) for result in results],
    )
