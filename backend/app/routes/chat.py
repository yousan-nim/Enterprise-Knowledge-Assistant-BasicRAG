import httpx
from fastapi import APIRouter, HTTPException
from app.api_docs.api_docs import CHAT_ERRORS
from app.schemas.http import ChatRequest, ChatResponse
from app.services.ollama import generate_answer

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, tags=["Chat"],
          summary="Ask the model without retrieval",
          description="Calls the local chat model directly. Does not read the indexed document or return citations.",
          responses=CHAT_ERRORS)
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
