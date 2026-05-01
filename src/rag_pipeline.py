import ollama
import chromadb
from openai import OpenAI
from opentelemetry import trace as otel_trace, context as otel_ctx
from opentelemetry.trace import StatusCode

from config import LLM_MODEL, EMBED_MODEL, CHROMA_PATH, CHROMA_COLLECTION, TOP_K, OLLAMA_BASE_URL
from tracing import get_tracer

# OpenAI-compatible client pointing at Ollama — auto-instrumented by OpenInference.
openai_client = OpenAI(base_url=f"{OLLAMA_BASE_URL}/v1", api_key="ollama")

PROMPTS = {
    "factual": (
        "You are a film expert. Answer the user's question using ONLY the films provided below.\n"
        "STRICT RULE: if the exact information is not explicitly written in the context below, "
        "respond ONLY with: 'I don't have that specific information in my database.'\n"
        "Do NOT use any external knowledge.\n\n"
        "Films:\n{context}\n\n"
        "Question: {query}\n"
        "Answer:"
    ),
    "recommendation": (
        "You are a film expert. Recommend films to the user based ONLY on the films provided below.\n"
        "For each recommendation explain briefly why it matches the request.\n\n"
        "Available films:\n{context}\n\n"
        "User request: {query}\n"
        "Recommendations:"
    ),
    "comparison": (
        "You are a film expert. Compare the films based ONLY on the information provided below.\n"
        "Highlight differences in style, tone, director and themes.\n\n"
        "Films:\n{context}\n\n"
        "User request: {query}\n"
        "Comparison:"
    ),
}


# Embeds the query with Ollama and retrieves the top-K most similar films from ChromaDB.
def retrieve(query: str) -> list[dict]:
    client     = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(CHROMA_COLLECTION)
    query_vec  = ollama.embeddings(model=EMBED_MODEL, prompt=query)["embedding"]
    results    = collection.query(query_embeddings=[query_vec], n_results=TOP_K)

    return [
        {"document": doc, "metadata": meta}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


# Formats the retrieved documents into a numbered context string for the prompt.
def build_context(docs: list[dict]) -> str:
    return "\n\n---\n\n".join(d["document"] for d in docs)


# Calls the LLM via OpenAI-compatible client (Ollama) and returns the full response string.
# Non-streaming so that OpenInference captures the complete output in Phoenix.
def generate(query: str, intent: str, context: str) -> str:
    prompt   = PROMPTS[intent].format(context=context, query=query)
    response = openai_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=False,
    )
    return response.choices[0].message.content or ""


# Full RAG pipeline with nested OTel spans: rag.run → rag.retrieve + rag.generate → ChatCompletion.
# Returns (full_response, docs) — non-streaming so Phoenix can record the complete answer.
def run(query: str, intent: str) -> tuple[str, list[dict]]:
    tracer = get_tracer()

    run_span  = tracer.start_span("rag.run")
    run_ctx   = otel_trace.set_span_in_context(run_span)
    run_token = otel_ctx.attach(run_ctx)
    try:
        run_span.set_attribute("openinference.span.kind", "CHAIN")
        run_span.set_attribute("input.value", query)
        run_span.set_attribute("rag.intent", intent)

        with tracer.start_as_current_span("rag.retrieve") as ret_span:
            docs = retrieve(query)
            titles = ", ".join(d["metadata"]["title"] for d in docs)
            ret_span.set_attribute("openinference.span.kind", "RETRIEVER")
            ret_span.set_attribute("input.value", query)
            ret_span.set_attribute("output.value", titles)
            ret_span.set_attribute("rag.num_docs", len(docs))
            ret_span.set_status(StatusCode.OK)

        context_str = build_context(docs)

        with tracer.start_as_current_span("rag.generate") as gen_span:
            answer = generate(query, intent, context_str)
            gen_span.set_attribute("openinference.span.kind", "CHAIN")
            gen_span.set_attribute("input.value", query)
            gen_span.set_attribute("output.value", answer)
            gen_span.set_status(StatusCode.OK)

        run_span.set_attribute("output.value", answer[:2000])
        run_span.set_status(StatusCode.OK)
    finally:
        otel_ctx.detach(run_token)
        run_span.end()

    return answer, docs
