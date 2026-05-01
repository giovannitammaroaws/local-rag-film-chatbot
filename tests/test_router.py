from unittest.mock import patch

from src.router import classify_intent, route


class _Choice:
    def __init__(self, content):
        self.message = type("Message", (), {"content": content})()


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]


@patch("src.router.openai_client.chat.completions.create")
def test_classify_intent_falls_back_to_recommendation(mock_create):
    mock_create.return_value = _Response("something-else")

    label = classify_intent("surprise me")

    assert label == "recommendation"


def test_route_blocks_when_guardrail_rejects():
    with patch("src.router.classify_intent", return_value="factual"), patch(
        "src.router.guardrail_check", return_value=(False, "blocked")
    ), patch("src.router.GUARDRAIL_ENABLED", True):
        intent, rejection = route("bad request")

    assert intent is None
    assert rejection == "blocked"


def test_route_skips_guardrail_when_disabled():
    with patch("src.router.classify_intent", return_value="comparison"), patch(
        "src.router.GUARDRAIL_ENABLED", False
    ):
        intent, rejection = route("compare these")

    assert intent == "comparison"
    assert rejection is None
