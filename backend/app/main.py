import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from pathlib import Path

from app.services.ollama import generate_answer
from app.services.generation import answer_from_document

app = FastAPI(
    title="Enterprise Knowledge Assistant",
    version="0.1.0",
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HANDBOOK_PATH = PROJECT_ROOT / "samples" / "company-handbook.md"


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str


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


@app.post("/questions", response_model=ChatResponse)
async def ask_document(body: ChatRequest):
    question = body.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Please enter a question.",
        )

    try:
        context = HANDBOOK_PATH.read_text(encoding="utf-8")
    except OSError:
        raise HTTPException(
            status_code=503,
            detail="The sample handbook is unavailable.",
        )

    if not context.strip():
        raise HTTPException(
            status_code=503,
            detail="The sample handbook is empty.",
        )

    try:
        answer = await answer_from_document(question, context)
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