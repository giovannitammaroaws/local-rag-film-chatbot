import ollama
from config import LLM_MODEL, GUARD_MODEL

# Rejection messages returned to the user when a check fails.
MSG_UNSAFE    = "I'm sorry, I can't help with that request."
MSG_OFF_TOPIC = "I can only answer questions about films and cinema. Try asking me for a movie recommendation or facts about a director."


# Calls Llama Guard 3 1B to detect harmful or unsafe content.
# Returns True if the query is safe to process.
def is_safe(query: str) -> bool:
    response = ollama.chat(
        model=GUARD_MODEL,
        messages=[{"role": "user", "content": query}],
    )
    return response.message.content.strip().lower().startswith("safe")


# Asks the LLM whether the query is related to films or cinema.
# Returns True if the topic is relevant.
def is_film_related(query: str) -> bool:
    response = ollama.chat(
        model=LLM_MODEL,
        messages=[{
            "role": "user",
            "content": (
                "You are a strict classifier. Reply YES only if the question is DIRECTLY about films, "
                "cinema, movie directors, actors, screenwriters, film awards, or specific movies. "
                "Reply NO for anything else — recipes, sports, politics, general knowledge, greetings, etc. "
                "Reply with exactly one word: YES or NO.\n"
                f"Question: {query}"
            ),
        }],
    )
    return "YES" in response.message.content.upper()


# Runs both guardrail checks in order: safety first, then topic relevance.
# Returns (passed: bool, rejection_message: str | None).
def check(query: str) -> tuple[bool, str | None]:
    if not is_safe(query):
        return False, MSG_UNSAFE
    if not is_film_related(query):
        return False, MSG_OFF_TOPIC
    return True, None
