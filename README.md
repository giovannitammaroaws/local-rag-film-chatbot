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

## Answer, inference and RAGAS evaluation

### 1. Answer

![Answer shown in the chatbot UI](images/answer.png)

The `Answer` is the final response returned to the user in the chatbot UI.
It is produced after the RAG pipeline has accepted the question, retrieved the
most relevant film documents from ChromaDB, built the context, and asked the LLM
to generate a grounded answer from that context.

In other words, this is the user-facing result of inference: the model has
already used the retrieved context and has produced the final natural-language
response.

### 2. Inference trace

![Phoenix trace showing the RAG inference flow](images/LLM_1.png)

Phoenix records the inference flow as a trace. A typical query starts from
`rag-film-chatbot.query`, then enters the RAG pipeline through `rag.run`.
Inside that run, the application retrieves context with `rag.retrieve` and
then generates the final answer with `rag.generate`.

In `LLM_1`, Phoenix shows the request as five readable trace sections:

- `rag-film-chatbot.query`: the parent trace for the whole user request. It
  starts when the user sends the question from the Gradio UI and ends when the
  answer is ready.
- first `ChatCompletion`: the router/classifier LLM call. It reads the user
  question and decides whether the intent is `factual`, `recommendation`, or
  `comparison`. In the screenshot, the output is `factual`.
- `rag.run`: the main RAG pipeline container. It receives the original query
  plus the detected intent and coordinates retrieval and generation.
- `rag.retrieve`: the retriever step. It searches ChromaDB for the most relevant
  film documents, using embeddings and exact title matching when possible.
- `rag.generate` and its nested `ChatCompletion`: the generation step. It builds
  the final prompt from the user question plus retrieved context, then calls the
  LLM to produce the final answer shown in the UI.

The `ChatCompletion` spans are the real LLM calls. The manual `rag.*` spans are
the application-level steps we created so Phoenix can show where the time is
spent and which part of the pipeline produced each result.

### 3. LLM calls breakdown

![Phoenix spans table showing five ChatCompletion calls](images/LLM_2.png)

At this point the chatbot has already answered `"Christopher Nolan."` to the
question `"Who directed Inception?"`. Clicking **Evaluate this answer** triggers
RAGAS, which uses a judge model (`qwen2.5:3b`) to measure the answer quality.
RAGAS has no access to ground truth — it only has the answer, the question, and
the retrieved documents. It asks the judge two questions, producing **5 LLM
calls in total**:

```
faithfulness      → 2 calls
answer relevancy  → 3 calls
──────────────────────────────
1 evaluated sample → 5 calls   (N samples → 5×N calls)
```

**Question 1 — Did the chatbot invent anything, or did it stick to what it retrieved? (`faithfulness`)**

RAGAS cannot look up facts externally. Instead it checks whether the answer is
supported by the documents that the RAG pipeline actually retrieved.

- **Call 1** asks the judge: *"Turn the answer into a verifiable statement."*
  `"Christopher Nolan."` → `"Christopher Nolan directed a film."`
  This is a preparation step — a short answer must become a checkable claim.

- **Call 5** asks the judge: *"Is this statement present in the retrieved documents?"*
  The Inception document contains `Director: Christopher Nolan` → `verdict: 1` ✓

The two calls are not the same: the first one **prepares** the claim, the second
one **verifies** it. Both are required because the LLM answer is free text, not
a structured fact.

**Question 2 — Did the chatbot actually answer the question that was asked? (`answer relevancy`)**

RAGAS uses a reverse trick: instead of directly comparing the answer to the
question, it asks the judge *"If someone answered 'Christopher Nolan.', what
question were they probably answering?"* — then compares that generated question
to the original. If they match, the answer was on-topic.

This is done **3 times** (Calls 2, 3, 4) with the same input, because the judge
is probabilistic and a single attempt could be a lucky or unlucky sample. Three
attempts give a more stable average:

| Call | Judge output | Match with `"Who directed Inception?"` |
|------|-------------|----------------------------------------|
| 2 | `"Who is Christopher Nolan?"` | Partial — right person, wrong angle |
| 3 | `"Who directed the Dark Knight film series?"` | No — wrong film entirely |
| 4 | `"Who is Christopher Nolan?"` | Partial — same as Call 2 |

RAGAS embeds all three generated questions and the original question, computes
cosine similarity for each pair, and averages the three scores. Call 3 (wrong
film) pulls the final `answer relevancy` score below 1.0. The root cause: the
answer `"Christopher Nolan."` is too short to uniquely imply `Inception` — it
could be the answer to many questions about Nolan.

The bottom `rag-film-chatbot.query` row in the screenshot is a `chain` span, not
an `llm` span — it wraps the entire request lifecycle from user question to
final answer, and is not one of the five LLM calls.


### 4. Evaluation after inference

Evaluation happens after inference. The answer is already generated first; only
then the user can run evaluation on that answer.

The evaluation step creates a RAGAS sample composed of:

- the original user question
- the generated answer
- the retrieved contexts used by the RAG pipeline

RAGAS then uses the judge model (`qwen2.5:3b`) to score the answer. In this
project the evaluation focuses on:

- `faithfulness`: whether the answer is grounded in the retrieved context
- `answer relevancy`: whether the answer actually responds to the user query

So the flow is:

```text
Question -> RAG inference -> Answer -> RAGAS evaluation -> Scores
```

The important distinction is that evaluation does not generate the answer. It
checks the quality of an answer that was already produced by inference.

## RAGAS

RAGAS is the evaluation layer used after the RAG answer has already been
generated. It does not replace the RAG pipeline and it does not create the
answer shown to the user.

In this project RAGAS receives:

- the original user question
- the answer generated by the chatbot
- the retrieved contexts used during inference

Then it asks a local judge model (`qwen2.5:3b`) to score the answer.

### Faithfulness

`faithfulness` checks whether the generated answer is supported by the
retrieved context.

A high faithfulness score means the answer is grounded in the documents that
were retrieved from ChromaDB. A low score means the model may have added facts
that are not present in the retrieved context, which is a hallucination risk.

Example:

- good: the answer says only things that appear in the retrieved film data
- bad: the answer invents a director, year, actor, plot detail, or genre that
  was not retrieved

### Answer relevancy

`answer relevancy` checks whether the generated answer actually responds to the
user question.

A high answer relevancy score means the answer is on-topic and useful for the
question that was asked. A low score means the answer may be generic, partial,
off-topic, or focused on the wrong part of the request.

Example:

- good: the user asks for a noir recommendation and the answer recommends noir
  films with a reason
- bad: the user asks for a comparison and the answer only gives a generic movie
  summary

## Requirements

- Python 3.11+
- Ollama installed and running
- Docker Desktop, if you want Phoenix tracing

> 🪟 **Windows only:** use **Python 3.11** (not 3.12/3.13). `chromadb` ships pre-built wheels only for 3.11 on Windows — newer versions will fail to install with a C++ compiler error.

## Setup

### 1. Enter the project folder

```bash
cd local-rag-film-chatbot
```

### 2. Create and activate a virtual environment

🐧 **Linux / macOS**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

🪟 **Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> If PowerShell blocks the script with an execution-policy error, run once:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

🪟 **Windows (Command Prompt)**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Install dependencies

🐧 **Linux / macOS**
```bash
.venv/bin/python -m pip install -r requirements.txt
```

🪟 **Windows**
```powershell
.venv\Scripts\python -m pip install -r requirements.txt
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

### 7. Index the dataset into ChromaDB (one-time only)

The TMDB dataset is already included in `data/`. This step only needs to be run once — it populates the local ChromaDB database. Skip it if `chroma_db/` already exists.

🐧 **Linux / macOS**
```bash
.venv/bin/python ingest.py
```

🪟 **Windows**
```powershell
.venv\Scripts\python ingest.py
```

### 8. Run the chatbot

🐧 **Linux / macOS**
```bash
.venv/bin/python chatbot.py
```

🪟 **Windows**
```powershell
.venv\Scripts\python chatbot.py
```

Open `http://127.0.0.1:7860`.

## Local quality gate — optional (contributors only)

> This section is intended for contributors who want to run automated checks before each commit. End users running the chatbot can skip this entirely.

Install the git hook once:

🐧 **Linux / macOS**
```bash
.venv/bin/python -m pre_commit install
```

🪟 **Windows**
```powershell
.venv\Scripts\python -m pre_commit install
```

From that point on, every `git commit` runs `pytest` first through `scripts/run-tests.sh`.

You can also run the same checks manually:

🐧 **Linux / macOS**
```bash
.venv/bin/python -m pre_commit run --all-files
```

🪟 **Windows**
```powershell
.venv\Scripts\python -m pre_commit run --all-files
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

🐧 **Linux / macOS**
```bash
.venv/bin/python chatbot.py
```

🪟 **Windows**
```powershell
.venv\Scripts\python chatbot.py
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

These values can be overridden before running the app.

🐧 **Linux / macOS**
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

🪟 **Windows (PowerShell)**
```powershell
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:GUARDRAIL_ENABLED="true"
$env:LLM_MODEL="llama3.2:3b"
$env:EMBED_MODEL="nomic-embed-text"
$env:JUDGE_MODEL="qwen2.5:3b"
$env:GUARD_MODEL="llama-guard3:1b"
$env:CHROMA_PATH="./chroma_db"
$env:CHROMA_COLLECTION="films"
$env:TOP_K="5"
```

🪟 **Windows (Command Prompt)**
```cmd
set OLLAMA_BASE_URL=http://localhost:11434
set GUARDRAIL_ENABLED=true
set LLM_MODEL=llama3.2:3b
set EMBED_MODEL=nomic-embed-text
set JUDGE_MODEL=qwen2.5:3b
set GUARD_MODEL=llama-guard3:1b
set CHROMA_PATH=./chroma_db
set CHROMA_COLLECTION=films
set TOP_K=5
```
