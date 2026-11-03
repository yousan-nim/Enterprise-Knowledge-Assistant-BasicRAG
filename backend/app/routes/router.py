from fastapi import APIRouter

from app.routes import chat, documents, health, questions

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(documents.router)
router.include_router(questions.router)
router.include_router(chat.router)
