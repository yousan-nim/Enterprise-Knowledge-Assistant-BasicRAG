import sqlite3
import httpx
from fastapi import APIRouter, HTTPException
from app.api_docs.api_docs import QUESTION_ERRORS, QUESTION_EXAMPLES
from app.schemas.http import QuestionRequest, QuestionResponse, RetrievedSource
from app.services.generation import answer_with_sources
from app.services.ollama import embed_texts
from app.services.retrieval import search_chunks
from app.storage.sqlite import get_chunks

router = APIRouter()


@router.post("/questions", response_model=QuestionResponse, tags=["RAG"],
          summary="Ask a question grounded in the indexed document",
          description="Embeds the question, ranks SQLite chunks by cosine similarity and generates a structured answer. Invalid model JSON or citation IDs can trigger one retry (two model attempts maximum). A valid response may still be factually wrong. No-answer responses currently use the canonical Thai message in any language.",
          responses={**QUESTION_ERRORS, **QUESTION_EXAMPLES})
async def ask_document(body: QuestionRequest):
    question = body.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Please enter a question.",
        )

    try:
        chunks = get_chunks()
    except ValueError as error:
        raise HTTPException(409, str(error))
    except (sqlite3.Error, OSError):
        raise HTTPException(503, "The document database is unavailable.")

    if not chunks:
        raise HTTPException(
            status_code=409,
            detail="Prepare a document with POST /api/v1/documents first.",
        )

    try:
        query_vector = (await embed_texts([question]))[0]

        results = search_chunks(
            query_vector=query_vector,
            chunks=chunks,
            top_k=body.top_k,
        )

        answer = await answer_with_sources(question, results)

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Ollama took too long to respond.",
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=503,
            detail="Cannot call Ollama. Check the app and models.",
        )
    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=502,
            detail="Retrieval or answer validation failed.",
        )

    return QuestionResponse(
        **answer.model_dump(),
        sources=[
            RetrievedSource(**result)
            for result in results
        ],
    )
