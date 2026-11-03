"""OpenAPI descriptions and examples; no application logic."""
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str | list[dict] = Field(description="Error message, or a list of request validation errors.")


class DocumentResponse(BaseModel):
    document_id: str = Field(description="ID of the newly stored document.", examples=["9e68fcaa-294f-49c1-8388-897fd28a24ab"])
    source: str = Field(description="Sanitized uploaded filename.", examples=["handbook.md"])
    chunks: int = Field(description="Number of indexed text chunks.", examples=[2])


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])


DESCRIPTION = """
Local document question answering with FastAPI, Ollama and SQLite.

## Try the workflow
1. Call **POST /api/v1/documents** with a UTF-8 TXT or Markdown file.
2. Call **POST /api/v1/questions** with a question and `top_k`.
3. Inspect `sources` to check the evidence behind `citation_ids`.

One document is stored at a time. A successful upload replaces it; failed ingestion preserves it.
SQLite retains the document and vectors across restarts. Re-upload after changing the embedding model,
including updating its weights under the same name.

`found` is derived from the model's answer, not an independent factual check.
Similarity scores are rankings, not confidence percentages. Valid citation IDs do not prove factual support.
The model may answer incorrectly or use a different language; review the cited text.

This is a local, single-user learning application with no authentication. Bind to loopback.
"""

TAGS = [
    {"name": "Health", "description": "Application liveness only; not an Ollama or database readiness check."},
    {"name": "Documents", "description": "Upload and index one TXT/Markdown document in SQLite."},
    {"name": "RAG", "description": "Retrieve document excerpts and generate structured, cited answers."},
    {"name": "Chat", "description": "Direct model chat without document retrieval."},
]


def errors(descriptions: dict[int, str]) -> dict:
    return {status: {"model": ErrorResponse, "description": description}
            for status, description in descriptions.items()}


CHAT_ERRORS = errors({
    422: "Missing/invalid request fields, or a whitespace-only question.",
    502: "Ollama returned an invalid or empty response.",
    503: "Ollama is unavailable or the chat model cannot be loaded.",
    504: "Ollama request timed out.",
})
QUESTION_ERRORS = errors({
    409: "No document is indexed, or its embedding model differs from the configured model. Upload again.",
    422: "Invalid question or top_k. A whitespace-only question is rejected.",
    502: "Retrieval, embedding or structured answer validation failed, including after the bounded retry.",
    503: "SQLite or Ollama is unavailable.",
    504: "Ollama request timed out.",
})
DOCUMENT_ERRORS = errors({
    413: "File exceeds 1 MiB, or extracted text exceeds 50,000 Python characters.",
    415: "Filename extension is not .txt or .md (case-insensitive). PDF is not supported.",
    422: "Missing file, invalid UTF-8, whitespace-only text, or null characters.",
    502: "The embedding response is invalid.",
    503: "Ollama is unavailable or the document cannot be saved to SQLite.",
    504: "Embedding request timed out.",
})

QUESTION_EXAMPLES = {
    "200": {
        "description": "Structured answer and retrieved evidence. Examples are illustrative, not guaranteed model output.",
        "content": {"application/json": {"examples": {
            "answered": {"summary": "Evidence contains an answer", "value": {
                "answer": "เบิกได้สูงสุด 500 บาทต่อวัน โดยต้องแนบใบเสร็จ",
                "citation_ids": ["chunk-2"], "found": True,
                "sources": [{"id": "chunk-2", "text": "Travel expenses are reimbursed up to THB 500 per day. Receipts are required.",
                             "source": "handbook.md", "score": 0.4279}]}},
            "not_found": {"summary": "Retrieved evidence does not answer the question", "value": {
                "answer": "ไม่พบข้อมูลในเอกสาร", "citation_ids": [], "found": False,
                "sources": [{"id": "chunk-1", "text": "Remote work is allowed two days per week.",
                             "source": "handbook.md", "score": 0.2818}]}}
        }}},
    }
}
