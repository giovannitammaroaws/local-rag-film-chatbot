from importlib import reload

import src.config as config


def test_defaults_are_loaded(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("TOP_K", raising=False)
    monkeypatch.delenv("GUARDRAIL_ENABLED", raising=False)

    reload(config)

    assert config.OLLAMA_BASE_URL == "http://localhost:11434"
    assert config.TOP_K == 5
    assert config.GUARDRAIL_ENABLED is True


def test_environment_overrides_are_respected(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://example.test:9999")
    monkeypatch.setenv("TOP_K", "7")
    monkeypatch.setenv("GUARDRAIL_ENABLED", "false")

    reload(config)

    assert config.OLLAMA_BASE_URL == "http://example.test:9999"
    assert config.TOP_K == 7
    assert config.GUARDRAIL_ENABLED is False
