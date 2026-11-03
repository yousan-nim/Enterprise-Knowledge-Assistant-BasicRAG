import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", os.getenv("DATA_DIR", str(BACKEND_DIR / "data"))))
EMBED_MODEL = "embeddinggemma"
