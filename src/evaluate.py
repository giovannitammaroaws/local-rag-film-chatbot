"""
RAGAS evaluation for CineRAG (RAGAS 0.2.x API).

Runs a small test set through the RAG pipeline and scores each answer on:
  - faithfulness:       does the answer stay within the retrieved context?
  - answer_relevancy:  does the answer address the question?

Uses qwen2.5:3b as judge (separate from the generation model to avoid self-eval bias).
"""

from ragas import evaluate as ragas_evaluate, EvaluationDataset, SingleTurnSample
from ragas.metrics import faithfulness, answer_relevancy
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaEmbeddings

from config import JUDGE_MODEL, EMBED_MODEL, OLLAMA_BASE_URL
from rag_pipeline import retrieve, build_context, generate
from router import classify_intent

TEST_QUERIES = [
    "Who directed The Dark Knight?",
    "Recommend me a sci-fi film about artificial intelligence",
    "How many Oscars did The Godfather win?",
    "Compare Inception and Interstellar",
    "I want a romantic comedy set in New York",
]


def _judge_llm() -> LangchainLLMWrapper:
    llm = ChatOpenAI(
        model=JUDGE_MODEL,
        base_url=f"{OLLAMA_BASE_URL}/v1",
        api_key="ollama",
        temperature=0,
    )
    return LangchainLLMWrapper(llm)


def _judge_embeddings() -> LangchainEmbeddingsWrapper:
    emb = OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_BASE_URL,
    )
    return LangchainEmbeddingsWrapper(emb)


def _run_query(query: str) -> dict:
    intent   = classify_intent(query)
    docs     = retrieve(query)
    ctx_str  = build_context(docs)
    answer   = generate(query, intent, ctx_str)
    contexts = [d["document"] for d in docs]
    return {"question": query, "answer": answer, "contexts": contexts}


def main():
    print(f"Running {len(TEST_QUERIES)} test queries through the RAG pipeline...\n")

    samples = []
    for i, q in enumerate(TEST_QUERIES, 1):
        print(f"  [{i}/{len(TEST_QUERIES)}] {q}")
        result = _run_query(q)
        samples.append(SingleTurnSample(
            user_input=result["question"],
            response=result["answer"],
            retrieved_contexts=result["contexts"],
        ))

    dataset = EvaluationDataset(samples=samples)

    print("\nScoring with RAGAS (judge: qwen2.5:3b)...\n")
    results = ragas_evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=_judge_llm(),
        embeddings=_judge_embeddings(),
        raise_exceptions=False,
    )

    df = results.to_pandas()
    faith_val     = float(df["faithfulness"].mean())
    relevancy_val = float(df["answer_relevancy"].mean())

    print("=" * 50)
    print(f"  Faithfulness:      {faith_val:.3f}  (1.0 = fully grounded in context)")
    print(f"  Answer Relevancy:  {relevancy_val:.3f}  (1.0 = perfectly on-topic)")
    print("=" * 50)

    print("\nPer-query breakdown:\n")
    print(df[["user_input", "faithfulness", "answer_relevancy"]].to_string(index=False))


if __name__ == "__main__":
    main()
