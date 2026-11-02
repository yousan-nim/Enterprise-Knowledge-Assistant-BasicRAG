import asyncio
from pathlib import Path

from app.services.chunking import chunk_text
from app.services.ollama import embed_texts
from app.services.retrieval import search_chunks

from app.services.generation import answer_with_sources


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HANDBOOK_PATH = PROJECT_ROOT / "samples" / "company-handbook.md"


async def main():
    # 1. Read and split the document.
    text = HANDBOOK_PATH.read_text(encoding="utf-8")
    texts = chunk_text(text, chunk_size=250, overlap=50)

    if not texts:
        raise ValueError("The handbook contains no text.")

    # 2. Create document embeddings once.
    vectors = await embed_texts(texts)

    chunks = [
        {
            "id": f"chunk-{index}",
            "text": chunk,
            "source": HANDBOOK_PATH.name,
            "embedding": vector,
        }
        for index, (chunk, vector) in enumerate(
            zip(texts, vectors),
            start=1,
        )
    ]

    print(f"Document: {HANDBOOK_PATH.name}")
    print(f"Chunks: {len(chunks)}")
    print(f"Embedding dimensions: {len(vectors[0])}")

    questions = [
        "ค่าเดินทางเบิกได้สูงสุดเท่าไร?",
        "ลาพักร้อนได้กี่วัน?",
    ]

    for question in questions:
        # 3. Embed the question using the same model.
        query_vector = (await embed_texts([question]))[0]

        # 4. Rank document chunks.
        results = search_chunks(
            query_vector=query_vector,
            chunks=chunks,
            top_k=2,
        )

        # 5. Inspect retrieved evidence before generating an answer.
        print("\n" + "=" * 60)
        print(f"Question: {question}")

        for rank, result in enumerate(results, start=1):
            print(f"\nRank: {rank}")
            print(f"Chunk: {result['id']}")
            print(f"Source: {result['source']}")
            print(f"Similarity: {result['score']:.4f}")
            print(f"Text:\n{result['text']}")
            
        try:
            answer = await answer_with_sources(question, results)
        except ValueError as error:
            print(f"\nStructured answer check: FAILED — {error}")
        else:
            print("\nStructured answer:")
            print(answer.model_dump_json(indent=2))
            print("Schema and citation IDs: PASSED")


if __name__ == "__main__":
    asyncio.run(main())
