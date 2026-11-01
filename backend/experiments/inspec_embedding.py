import asyncio

from app.services.chunking import chunk_text
from app.services.ollama import embed_texts


async def main():
    text = (
        "Employees can work remotely two days per week. "
        "Travel expenses are reimbursed up to 500 baht per day. "
        "Receipts are required for reimbursement."
    )

    chunks = chunk_text(text, chunk_size=80, overlap=20)
    vectors = await embed_texts(chunks)

    for index, (chunk, vector) in enumerate(
        zip(chunks, vectors),
        start=1,
    ):
        print(f"\nChunk {index}")
        print(f"Text: {chunk}")
        print(f"Dimensions: {len(vector)}")
        print(f"First 5 values: {vector[:5]}")


if __name__ == "__main__":
    asyncio.run(main())