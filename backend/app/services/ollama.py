import httpx
import math

from app.config.config import EMBED_MODEL

async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        raise ValueError("Please provide at least one text.")

    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("Each text must be a non-empty string.")

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            "http://127.0.0.1:11434/api/embed",
            json={
                "model": EMBED_MODEL,
                "input": texts,
                "truncate": False,
            },
        )

        response.raise_for_status()
        data = response.json()

    if not isinstance(data, dict):
        raise ValueError("Invalid embedding response.")

    vectors = data.get("embeddings")

    if not isinstance(vectors, list) or len(vectors) != len(texts):
        raise ValueError("Embedding count does not match text count.")

    dimension = None

    for vector in vectors:
        if not isinstance(vector, list) or not vector:
            raise ValueError("Each embedding must be a non-empty list.")

        if dimension is None:
            dimension = len(vector)

        if len(vector) != dimension:
            raise ValueError("Embedding dimensions must match.")

        if any(
            type(value) not in (int, float) or not math.isfinite(value)
            for value in vector
        ):
            raise ValueError("Embedding values must be finite numbers.")

        if not any(vector):
            raise ValueError("Embedding must not be a zero vector.")

    return vectors


async def generate_answer(
    question: str,
    output_schema: dict | None = None,
) -> str:
    payload = {
        "model": "qwen2.5:3b",
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": question,
            }
        ],
    }

    if output_schema is not None:
        payload["format"] = output_schema
        payload["options"] = {"temperature": 0}

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            "http://127.0.0.1:11434/api/chat",
            json=payload,
        )

        response.raise_for_status()
        data = response.json()

    answer = data["message"]["content"]

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("The model returned an invalid or empty answer.")

    return answer.strip()
