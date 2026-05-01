from openai import OpenAI
from src.config import LLM_MODEL, LLM_BASE_URL, LLM_API_KEY, GUARD_MODEL

MSG_UNSAFE    = "I'm sorry, I can't help with that request."
MSG_OFF_TOPIC = "I can only answer questions about films and cinema. Try asking me for a movie recommendation or facts about a director."

_client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def is_safe(query: str) -> bool:
    response = _client.chat.completions.create(
        model=GUARD_MODEL,
        messages=[{"role": "user", "content": query}],
    )
    return response.choices[0].message.content.strip().lower().startswith("safe")


def is_film_related(query: str) -> bool:
    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{
            "role": "user",
            "content": (
                "You are a strict classifier. Reply YES only if the question is DIRECTLY about films, "
                "cinema, movie directors, actors, screenwriters, film awards, or specific movies. "
                "Reply NO for anything else - recipes, sports, politics, general knowledge, greetings, etc. "
                "Reply with exactly one word: YES or NO.\n"
                f"Question: {query}"
            ),
        }],
    )
    return "YES" in response.choices[0].message.content.upper()


def check(query: str) -> tuple[bool, str | None]:
    if not is_safe(query):
        return False, MSG_UNSAFE
    if not is_film_related(query):
        return False, MSG_OFF_TOPIC
    return True, None
