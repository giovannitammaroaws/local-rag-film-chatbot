# RAG Film Chatbot

A fully local RAG chatbot for film recommendations built with Ollama, ChromaDB, Phoenix, and RAGAS.

## Full pipeline - from client to RAGAS

```mermaid
flowchart TD
    U([User query<br/>Gradio UI]) --> G

    subgraph PIPE[RAG Pipeline]
        G["Guardrail<br/>llama-guard3:1b<br/>safety + topic check"]
        G -->|blocked| REJ([Rejection message])
        G -->|safe| RT["Router<br/>llama3.2:3b<br/>classify intent"]
        RT -->|factual / recommendation / comparison| RET["Retrieve<br/>nomic-embed-text to ChromaDB<br/>TOP_K films"]
        RET --> CTX[Build context<br/>from retrieved docs]
        CTX --> GEN["Generate<br/>llama3.2:3b<br/>answer from context"]
    end

    GEN --> ANS([Answer shown in UI])
    PIPE -.->|OTel spans| PH[(Phoenix<br/>localhost:6006)]

    ANS -->|click Evaluate this answer| RAGAS

    subgraph RAGAS[RAGAS Evaluation - qwen2.5:3b judge]
        S1["Create evaluation sample<br/>question + answer + contexts"] --> S2["Faithfulness<br/>grounded in retrieved context"]
        S1 --> S3["Answer relevancy<br/>on-topic with the query"]
    end

    S2 --> SCORE([Scores shown in UI])
    S3 --> SCORE
```

## Requirements

- Python 3.11+
- Ollama installed and running
- Docker Desktop, if you want Phoenix tracing

## Setup

### 1. Enter the project folder

```bash
cd local-rag-film-chatbot
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
.venv/bin/python -m pip install -r requirements.txt
```

### 4. Optional: customize configuration

Configuration is read from environment variables, with defaults defined in `src/config.py`.

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
.venv/bin/python ingest.py
```

### 8. Run the chatbot

```bash
.venv/bin/python chatbot.py
```

Open `http://127.0.0.1:7860`.

## Local quality gate

Install the git hook once:

```bash
.venv/bin/python -m pre_commit install
```

From that point on, every `git commit` runs `pytest` first through `scripts/run-tests.sh`.

You can also run the same checks manually:

```bash
.venv/bin/python -m pre_commit run --all-files
```

## Observability with Phoenix

This section assumes Docker is already installed on the user's machine.

Phoenix runs in Docker; the Python app sends traces with the OTLP HTTP exporter to `http://localhost:6006/v1/traces`.

If you want to avoid Docker overhead on the laptop, a practical alternative is Phoenix Cloud. Arize documents free Phoenix Cloud instances with 10 GiB of storage. In that setup you would point tracing to your Phoenix Cloud HTTP endpoint instead of `localhost`.

### 1. Start Phoenix

```bash
docker run -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest
```

### 2. Start the chatbot

```bash
.venv/bin/python chatbot.py
```

### 3. Open Phoenix

- Projects: `http://localhost:6006/projects`
- Traces appear under the `rag-film-chatbot` tracer after each query

## Project structure

```text
local-rag-film-chatbot/
├── chatbot.py
├── data/
├── evaluate.py
├── ingest.py
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
├── .gitignore
├── .pre-commit-config.yaml
└── requirements.txt
```

## Environment variables

These values can be overridden directly in the shell before running:

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
