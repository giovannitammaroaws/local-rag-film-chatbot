OLLAMA_BASE_URL = "http://localhost:11434"

# Set to False during development to skip the guardrail and save ~2-3s per query.
# Always set to True before recording the video.
GUARDRAIL_ENABLED = True

# Generation model
LLM_MODEL = "llama3.2:3b"

# Embedding model (for ChromaDB indexing and query encoding)
EMBED_MODEL = "nomic-embed-text"

# Judge model used by RAGAS (separate from generation to avoid self-eval bias)
JUDGE_MODEL = "qwen2.5:3b"

# Safety guardrail model (Meta Llama Guard 3 - purpose-built for input/output classification)
GUARD_MODEL = "llama-guard3:1b"

# ChromaDB
CHROMA_PATH       = "./chroma_db"
CHROMA_COLLECTION = "films"

# Retrieval
TOP_K = 5
