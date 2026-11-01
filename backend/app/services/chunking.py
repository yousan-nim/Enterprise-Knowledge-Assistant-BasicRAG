



def chunk_text(
    text: str, 
    chunk_size: int = 800,
    overlap: int = 120, 
) -> list[str]: 
    
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")
    
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be a non-negative integer less than chunk_size.")
    
    text = text.strip() 
    
    if not text: 
        return []
    
    chunks = [] 
    step = chunk_size - overlap 
    
    for start in range(0, len(text), step): 
        end = start + chunk_size
        chunks.append(text[start:end]) 
        
        if end >= len(text): 
            break 
        
    return chunks