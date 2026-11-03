from fastapi import APIRouter
from app.api_docs.api_docs import HealthResponse

router = APIRouter()


@router.get("/health", tags=["Health"], summary="Check API liveness",
         description="Returns ok when the application responds. Does not check Ollama, installed models or SQLite.",
         response_model=HealthResponse)
def health():
    return {"status": "ok"}
