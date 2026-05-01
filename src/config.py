import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Set to False during development to skip the guardrail and save ~2-3s per query.
# Always set to True before recording the video.
GUARDRAIL_ENABLED = _get_bool("GUARDRAIL_ENABLED", True)

# Generation model
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")

# Embedding model (for ChromaDB indexing and query encoding)
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# Judge model used by RAGAS (separate from generation to avoid self-eval bias)
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "qwen2.5:3b")

# Safety guardrail model (Meta Llama Guard 3 - purpose-built for input/output classification)
GUARD_MODEL = os.getenv("GUARD_MODEL", "llama-guard3:1b")

# ChromaDB
CHROMA_PATH = os.getenv("CHROMA_PATH", str(ROOT / "chroma_db"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "films")

# Retrieval
TOP_K = _get_int("TOP_K", 5)
