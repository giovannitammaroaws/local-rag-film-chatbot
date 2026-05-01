import math
import gradio as gr
from datetime import datetime
from opentelemetry import trace as otel_trace, context as otel_ctx
from opentelemetry.trace import StatusCode
from ragas import evaluate as ragas_evaluate, EvaluationDataset, SingleTurnSample
from ragas.metrics import faithfulness, answer_relevancy

from src.config import LLM_MODEL
from src.router import route
from src.rag_pipeline import run as rag_run
from src.tracing import init_tracing, get_tracer
from src.evaluate import _run_query, _judge_llm, _judge_embeddings, TEST_QUERIES

EXAMPLES = [
    "Recommend me a sci-fi film about artificial intelligence",
    "Who directed Inception?",
    "Is The Godfather better than Goodfellas?",
    "I want something scary for Halloween night",
    "How many Oscars did The Godfather win?",
]


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _process(msg: str) -> tuple[str | None, str | None, str, list[dict]]:
    tracer = get_tracer()

    root_span  = tracer.start_span("cinerag.query")
    root_ctx   = otel_trace.set_span_in_context(root_span)
    root_token = otel_ctx.attach(root_ctx)
    try:
        root_span.set_attribute("openinference.span.kind", "CHAIN")
        root_span.set_attribute("input.value", msg)

        intent, rejection = route(msg)

        if rejection:
            root_span.set_attribute("output.value", rejection)
            root_span.set_status(StatusCode.ERROR, rejection)
            return None, rejection, "", []

        full_response, docs = rag_run(msg, intent)
        root_span.set_attribute("output.value", full_response)
        root_span.set_attribute("intent", intent)
        root_span.set_status(StatusCode.OK)
        return intent, None, full_response, docs
    finally:
        otel_ctx.detach(root_token)
        root_span.end()


def respond(msg: str, history: list, log: str, total_cost: float):
    log += f"[{_ts()}] Query: \"{msg}\"\n"
    history.append({"role": "user",      "content": msg})
    history.append({"role": "assistant", "content": "..."})
    yield "", history, "_Processing..._", "", "", "", log, total_cost, None

    intent, rejection, full_response, retrieved_docs = _process(msg)

    if rejection:
        history[-1]["content"] = rejection
        log += f"[{_ts()}] BLOCKED: {rejection}\n" + "-" * 40 + "\n"
        yield "", history, "**Blocked**", "", "", "", log, total_cost, None
        return

    history[-1]["content"] = full_response
    log += f"[{_ts()}] Intent: {intent.upper()}\n"

    input_tok  = sum(len(d["document"].split()) for d in retrieved_docs) + len(msg.split())
    output_tok = len(full_response.split())
    cost       = round(input_tok / 1000 * 0.01 + output_tok / 1000 * 0.03, 6)
    total_cost = round(total_cost + cost, 6)

    titles  = ", ".join(d["metadata"]["title"] for d in retrieved_docs)
    log += f"[{_ts()}] Retrieved: {titles}\n"
    log += f"[{_ts()}] Output tokens: {output_tok} | Cost: ${cost:.6f}\n"
    log += "-" * 40 + "\n"

    token_md = f"**Tokens:** `{input_tok}` in / `{output_tok}` out"
    cost_md  = f"**Query cost:** `${cost:.6f}`\n\n**Session total:** `${total_cost:.6f}`"
    docs_md  = f"**Retrieved:**\n" + "\n".join(
        f"- {d['metadata']['title']} ({d['metadata']['year']})" for d in retrieved_docs
    )

    last_result = {
        "question": msg,
        "answer":   full_response,
        "contexts": [d["document"] for d in retrieved_docs],
    }

    yield "", history, f"**Intent:** `{intent.upper()}`", token_md, cost_md, docs_md, log, total_cost, last_result


def evaluate_single_answer(last_result, progress=gr.Progress(track_tqdm=True)):
    if last_result is None:
        yield "_Send a message first._", "", ""
        return

    progress(0.1, desc="Scoring with RAGAS...")
    yield "_Scoring with RAGAS (judge: qwen2.5:3b)..._", "", ""

    sample  = SingleTurnSample(
        user_input=last_result["question"],
        response=last_result["answer"],
        retrieved_contexts=last_result["contexts"],
    )
    dataset = EvaluationDataset(samples=[sample])
    results = ragas_evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=_judge_llm(),
        embeddings=_judge_embeddings(),
        raise_exceptions=False,
    )

    df          = results.to_pandas()
    faith_val   = float(df["faithfulness"].iloc[0])
    rel_val     = float(df["answer_relevancy"].iloc[0]) if "answer_relevancy" in df.columns else float("nan")

    faith_str = f"`{faith_val:.3f}`" if not math.isnan(faith_val) else "`N/A`"
    rel_str   = f"`{rel_val:.3f}`"   if not math.isnan(rel_val)   else "`N/A`"

    progress(1.0, desc="Done!")
    yield (
        "**Evaluation complete.**",
        f"**Faithfulness:** {faith_str}\n\n_grounded in retrieved context_",
        f"**Answer Relevancy:** {rel_str}\n\n_on-topic with the query_",
    )


def run_evaluation(progress=gr.Progress(track_tqdm=True)):
    n = len(TEST_QUERIES)
    progress(0, desc="Starting...")
    yield "_Starting evaluation..._", "", "", gr.DataFrame(visible=False)

    samples = []
    for i, q in enumerate(TEST_QUERIES, 1):
        progress(i / (n * 2), desc=f"Query {i}/{n}")
        yield f"_Running query {i}/{n}:_ `{q}`", "", "", gr.DataFrame(visible=False)
        result = _run_query(q)
        samples.append(SingleTurnSample(
            user_input=result["question"],
            response=result["answer"],
            retrieved_contexts=result["contexts"],
        ))

    progress(0.6, desc="Scoring with RAGAS (qwen2.5:3b)...")
    yield f"_All {n} queries done. Scoring with RAGAS (judge: qwen2.5:3b)..._", "", "", gr.DataFrame(visible=False)

    dataset = EvaluationDataset(samples=samples)
    results = ragas_evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=_judge_llm(),
        embeddings=_judge_embeddings(),
        raise_exceptions=False,
    )

    df = results.to_pandas()
    faith_val     = float(df["faithfulness"].mean())
    relevancy_val = float(df["answer_relevancy"].mean()) if "answer_relevancy" in df.columns else float("nan")

    display_df = df[["user_input", "faithfulness", "answer_relevancy"]].copy()
    display_df.columns = ["Question", "Faithfulness", "Answer Relevancy"]

    relevancy_str = f"## {relevancy_val:.3f}" if not math.isnan(relevancy_val) else "## N/A"

    progress(1.0, desc="Done!")
    yield (
        "**Evaluation complete.**",
        f"## {faith_val:.3f}\n_Faithfulness_ - answers grounded in retrieved context",
        f"{relevancy_str}\n_Answer Relevancy_ - answers on-topic with the query",
        gr.DataFrame(value=display_df, visible=True),
    )


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="RAG Film Chatbot") as demo:

        gr.Markdown("# RAG Film Chatbot\n"
                    "_Ollama - ChromaDB - Phoenix - RAGAS_")

        total_cost_state  = gr.State(0.0)
        last_result_state = gr.State(None)

        with gr.Tabs():

            with gr.Tab("Chat"):
                with gr.Row():
                    with gr.Column(scale=3):
                        chatbot  = gr.Chatbot(value=[], height=450, label="Chat")
                        with gr.Row():
                            msg_box  = gr.Textbox(
                                placeholder='"Recommend a sci-fi film" - "Who directed Inception?" - "Godfather vs Goodfellas?"',
                                scale=8, container=False,
                            )
                            send_btn = gr.Button("Send", scale=1, variant="primary")
                        gr.Examples(examples=EXAMPLES, inputs=msg_box)

                    with gr.Column(scale=1):
                        gr.Markdown("## Live Info")
                        intent_out = gr.Markdown("_Waiting for a query..._")
                        token_out  = gr.Markdown("")
                        cost_out   = gr.Markdown("")
                        docs_out   = gr.Markdown("")

                        gr.Markdown("---")
                        eval_btn_single  = gr.Button("Evaluate this answer", variant="secondary", size="sm")
                        eval_single_status = gr.Markdown("")
                        eval_single_faith  = gr.Markdown("")
                        eval_single_rel    = gr.Markdown("")

                        gr.Markdown("---")
                        gr.Markdown("[Phoenix Dashboard](http://localhost:6006)")
                        gr.Markdown(f"`{LLM_MODEL}` via Ollama")
                        gr.Markdown("ChromaDB - 4799 TMDB films")

                gr.Markdown("### Pipeline Log")
                log_box = gr.Textbox(
                    value="", lines=8, max_lines=8,
                    label="", interactive=False,
                    placeholder="Pipeline log will appear here...",
                )

                inputs  = [msg_box, chatbot, log_box, total_cost_state]
                outputs = [msg_box, chatbot, intent_out, token_out, cost_out, docs_out, log_box, total_cost_state, last_result_state]

                msg_box.submit(respond, inputs, outputs)
                send_btn.click(respond, inputs, outputs)

                eval_btn_single.click(
                    evaluate_single_answer,
                    inputs=[last_result_state],
                    outputs=[eval_single_status, eval_single_faith, eval_single_rel],
                )

            with gr.Tab("Evaluate"):
                gr.Markdown("## RAGAS Evaluation\n"
                            f"Runs {len(TEST_QUERIES)} test queries through the pipeline and scores with "
                            "`faithfulness` and `answer_relevancy` using `qwen2.5:3b` as judge.")

                eval_btn    = gr.Button("Run Evaluation", variant="primary", size="lg")
                eval_status = gr.Markdown("_Click the button to start..._")

                with gr.Row():
                    faith_out     = gr.Markdown("")
                    relevancy_out = gr.Markdown("")

                eval_table = gr.DataFrame(
                    headers=["Question", "Faithfulness", "Answer Relevancy"],
                    visible=False,
                )

                eval_btn.click(
                    run_evaluation,
                    outputs=[eval_status, faith_out, relevancy_out, eval_table],
                )

    return demo


def main():
    init_tracing()
    demo = build_ui()
    demo.launch(
        theme=gr.themes.Soft(),
        css="footer { display: none !important; }",
        ssr_mode=False,
    )


if __name__ == "__main__":
    main()
