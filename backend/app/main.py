import sqlite3
import httpx
from pydantic import BaseModel, Field
from fastapi import FastAPI, File, HTTPException, UploadFile
from app.services.ingestion import ingest_text

from pathlib import Path

from app.services.ollama import generate_answer
from app.schemas import GroundedAnswer
from app.services.generation import answer_with_sources
from app.services.ollama import embed_texts
from app.services.retrieval import search_chunks
from app.storage.sqlite import get_chunks

app = FastAPI(
    title="Enterprise Knowledge Assistant",
    version="0.1.0",
)



class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=10)
    
class RetrievedSource(BaseModel):
    id: str
    text: str
    source: str
    score: float
    
class QuestionResponse(GroundedAnswer):
    sources: list[RetrievedSource]

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    question = body.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Please enter a question.",
        )

    try:
        answer = await generate_answer(question)
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Ollama took too long to respond.",
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=503,
            detail="Cannot call Ollama. Check the app and installed model.",
        )
    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=502,
            detail="Ollama returned an invalid response.",
        )

    return ChatResponse(answer=answer)


@app.post("/questions", response_model=QuestionResponse)
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
            detail="Prepare a document with POST /documents first.",
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
 
 
MAX_UPLOAD_BYTES = 1024 * 1024
MAX_TEXT_CHARACTERS = 50_000


@app.post("/documents", status_code=201)
async def prepare_document(file: UploadFile = File(...)):
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
