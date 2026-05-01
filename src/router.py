from openai import OpenAI

from src.guardrail import check as guardrail_check
from src.config import LLM_MODEL, OLLAMA_BASE_URL, GUARDRAIL_ENABLED

# OpenAI-compatible client pointing at Ollama - auto-instrumented by OpenInference.
openai_client = OpenAI(base_url=f"{OLLAMA_BASE_URL}/v1", api_key="ollama")

INTENT_PROMPT = """Classify the user query into one of three categories:

- factual: user wants a specific fact about a film (director, year, cast, Oscar, budget)
- recommendation: user wants personalized film recommendations
- comparison: user wants to compare two or more films

Reply with exactly one word: factual, recommendation, or comparison.

Query: {query}
Category:"""


# Sends the query to the LLM and returns one of the three intent labels.
def classify_intent(query: str) -> str:
    response = openai_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{
            "role": "user",
            "content": INTENT_PROMPT.format(query=query),
        }],
    )
    label = response.choices[0].message.content.strip().lower()

    if label not in ("factual", "recommendation", "comparison"):
        return "recommendation"
    return label


# Main router entry point. Runs guardrail checks first, then classifies intent.
# Returns (intent: str | None, rejection_message: str | None).
def route(query: str) -> tuple[str | None, str | None]:
    if GUARDRAIL_ENABLED:
        passed, rejection = guardrail_check(query)
        if not passed:
            return None, rejection

    intent = classify_intent(query)
    return intent, None
