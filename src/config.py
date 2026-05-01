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


GROQ_API_KEY  = os.getenv("GROQ_API_KEY")
USE_GROQ      = bool(GROQ_API_KEY)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

if USE_GROQ:
    LLM_BASE_URL = "https://api.groq.com/openai/v1"
    LLM_API_KEY  = GROQ_API_KEY
    LLM_MODEL    = os.getenv("LLM_MODEL",   "llama-3.1-8b-instant")
    JUDGE_MODEL  = os.getenv("JUDGE_MODEL", "llama-3.1-8b-instant")
    GUARD_MODEL  = os.getenv("GUARD_MODEL", "llama-guard-3-8b")
    EMBED_MODEL  = "nomic-ai/nomic-embed-text-v1.5"
else:
    LLM_BASE_URL = f"{OLLAMA_BASE_URL}/v1"
    LLM_API_KEY  = "ollama"
    LLM_MODEL    = os.getenv("LLM_MODEL",   "llama3.2:3b")
    JUDGE_MODEL  = os.getenv("JUDGE_MODEL", "qwen2.5:3b")
    GUARD_MODEL  = os.getenv("GUARD_MODEL", "llama-guard3:1b")
    EMBED_MODEL  = os.getenv("EMBED_MODEL", "nomic-embed-text")

GUARDRAIL_ENABLED  = _get_bool("GUARDRAIL_ENABLED", True)
CHROMA_PATH        = os.getenv("CHROMA_PATH", str(ROOT / "chroma_db"))
CHROMA_COLLECTION  = os.getenv("CHROMA_COLLECTION", "films")
TOP_K              = _get_int("TOP_K", 5)
