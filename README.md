# RAG Film Chatbot

A fully local RAG chatbot for film recommendations built with Ollama, ChromaDB, Phoenix, and RAGAS.

## Requirements

- Python 3.11+
- Ollama installed and running
- Docker Desktop, if you want Phoenix tracing

## Setup

### 1. Enter the project folder

```bash
cd cinerag
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Optional: customize configuration

Copy `.env.example` to `.env` and edit values only if you need different models, ports, or paths.

```bash
cp .env.example .env
```

Current configuration is read from environment variables, with defaults defined in `src/config.py`.

### 5. Start Ollama

```bash
ollama serve
```

### 6. Pull the Ollama models

```bash
ollama pull nomic-embed-text
ollama pull llama3.2:3b
ollama pull llama-guard3:1b
ollama pull qwen2.5:3b
```

### 7. Index the dataset into ChromaDB

The TMDB dataset is already included in `data/`.

```bash
python3 ingest.py
```

### 8. Run the chatbot

```bash
python3 chatbot.py
```

Open `http://127.0.0.1:7860`.

## Local quality gate

Install the git hook once:

```bash
pre-commit install
```

From that point on, every `git commit` runs `pytest` first through `scripts/run-tests.sh`.

You can also run the same checks manually:

```bash
pre-commit run --all-files
```

## Observability with Phoenix

Phoenix runs in Docker; the Python app sends traces with the OTLP HTTP exporter to `http://localhost:6006/v1/traces`.

### 1. Start Phoenix

```bash
docker run -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest
```

### 2. Start the chatbot

```bash
python3 chatbot.py
```

### 3. Open Phoenix

- Projects: `http://localhost:6006/projects`
- Traces appear under the `rag-film-chatbot` tracer after each query

## Project structure

```text
cinerag/
├── data/
├── scripts/
│   └── run-tests.sh
├── src/
│   ├── __init__.py
│   ├── chatbot.py
│   ├── config.py
│   ├── evaluate.py
│   ├── guardrail.py
│   ├── ingest.py
│   ├── rag_pipeline.py
│   ├── router.py
│   └── tracing.py
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
└── requirements.txt
```

## Environment variables

These values can be overridden in the shell or in a local `.env` file that you export manually before running:

```bash
export OLLAMA_BASE_URL=http://localhost:11434
export GUARDRAIL_ENABLED=true
export LLM_MODEL=llama3.2:3b
export EMBED_MODEL=nomic-embed-text
export JUDGE_MODEL=qwen2.5:3b
export GUARD_MODEL=llama-guard3:1b
export CHROMA_PATH=./chroma_db
export CHROMA_COLLECTION=films
export TOP_K=5
```
