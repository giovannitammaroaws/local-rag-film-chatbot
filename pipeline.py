import time
import random
from datetime import datetime

from classifier import classify, label_description
from responses import MOCK_RESPONSES

# Simulated pricing: $0.01 per 1k input tokens, $0.03 per 1k output tokens
# (approximates a cheap hosted LLM like Mistral Small or GPT-3.5-turbo)
PRICE_INPUT_PER_1K  = 0.01
PRICE_OUTPUT_PER_1K = 0.03

# Returns the current time formatted as HH:MM:SS for log entries.
def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


# Computes simulated cost given input and output token counts.
def compute_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1000 * PRICE_INPUT_PER_1K +
            output_tokens / 1000 * PRICE_OUTPUT_PER_1K)


# Builds the initial log block for a single query run.
def _build_log(msg: str, label: str, input_tok: int, output_tok: int, cost: float) -> str:
    t = _timestamp()
    lines = [
        f"[{t}] Query: \"{msg}\"",
        f"[{t}] Router -> {label.upper()}",
        f"[{t}] Retrieving docs from ChromaDB...",
        f"[{t}] Found 5 relevant films",
        f"[{t}] Input tokens: {input_tok} | Output tokens: {output_tok}",
        f"[{t}] Estimated cost: ${cost:.6f}",
        f"[{t}] Generating response...",
    ]
    return "\n".join(lines) + "\n"


# Main chat generator: classifies the query, streams the answer word by word,
# and yields updated history + sidebar metrics (including cost) on every token.
def respond(msg: str, history: list, log: str, total_cost: float):
    label       = classify(msg)
    answer      = random.choice(MOCK_RESPONSES[label])
    input_tok   = random.randint(40, 80)
    output_tok  = random.randint(60, 120)
    ragas       = round(random.uniform(0.78, 0.96), 2)

    query_cost  = compute_cost(input_tok, output_tok)
    total_cost  = round(total_cost + query_cost, 6)

    label_md = f"**Type:** `{label.upper()}`\n\n_{label_description(label)}_"
    token_md = f"**Tokens:** `{input_tok}` in / `{output_tok}` out"
    ragas_md = f"**RAGAS faithfulness:** `{ragas} / 1.00`"
    cost_md  = (f"**Query cost:** `${query_cost:.6f}`\n\n"
                f"**Session total:** `${total_cost:.6f}`")

    log += _build_log(msg, label, input_tok, output_tok, query_cost)

    history.append({"role": "user",      "content": msg})
    history.append({"role": "assistant", "content": ""})

    partial = ""
    for word in answer.split(" "):
        partial += word + " "
        history[-1]["content"] = partial
        time.sleep(0.04)
        yield "", history, label_md, token_md, ragas_md, cost_md, log, total_cost

    log += f"[{_timestamp()}] Done. RAGAS: {ragas}\n" + "-" * 40 + "\n"
    yield "", history, label_md, token_md, ragas_md, cost_md, log, total_cost
