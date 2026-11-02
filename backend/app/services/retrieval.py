import math 

def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        raise ValueError("Vectors must not be empty.")

    if len(a) != len(b):
        raise ValueError("Vectors must have the same dimensions.")

    for vector in (a, b):
        if any(
            type(value) not in (int, float) or not math.isfinite(value)
            for value in vector
        ):
            raise ValueError("Vector values must be finite numbers.")

    norm_a = math.hypot(*a)
    norm_b = math.hypot(*b)

    if norm_a == 0 or norm_b == 0:
        raise ValueError("Cannot compare zero vectors.")

    similarity = math.fsum(
        (x / norm_a) * (y / norm_b)
        for x, y in zip(a, b)
    )

    return max(-1.0, min(1.0, similarity))


def search_chunks(
    query_vector: list[float], 
    chunks: list[dict], 
    top_k: int = 3, 
) -> list[dict]: 
    
    if type(top_k) is not int or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")
    
    cosine_similarity(query_vector, query_vector)  # Validate query vector
    
    results = [] 
    
    for chunk in chunks:
        score = cosine_similarity(
            query_vector, 
            chunk["embedding"]
        )
        
        results.append({
             "id": chunk["id"],
            "text": chunk["text"],
            "source": chunk["source"],
            "score": score,
        })
    
    results.sort(key=lambda item: item["score"], reverse=True)

    return results[:top_k]
