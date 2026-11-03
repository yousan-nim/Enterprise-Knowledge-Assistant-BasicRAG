

_chunks: list[dict] = []

def replace_chunks(chunks: list[dict]) -> None: 
    global _chunks 
    _chunks = list(chunks)
    
def get_chunks() -> list[dict]: 
    return list(_chunks)
