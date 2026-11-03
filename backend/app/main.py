from fastapi import FastAPI

from app.api_docs.api_docs import DESCRIPTION, TAGS
from app.routes.router import router

app = FastAPI(
    title="Enterprise Knowledge Assistant",
    version="0.1.0",
    description=DESCRIPTION,
    openapi_tags=TAGS,
    swagger_ui_parameters={"displayRequestDuration": True, "docExpansion": "list"},
)

app.include_router(router)
