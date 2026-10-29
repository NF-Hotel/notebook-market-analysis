import pytest

from app.adapters.ai.lm_studio import LMStudioModelClient
from app.adapters.ai.ollama import OllamaModelClient
from app.application.insights import UnconfiguredInsightProvider
from app.application.model_insights import ModelInsightProvider
from app.infrastructure.config import Settings
from app.infrastructure.main import build_insight_provider


def _settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> Settings:
    monkeypatch.setenv("MARKET_DATA_API_URL", "https://market.example.com")
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return Settings(_env_file=None)


@pytest.mark.parametrize("provider", ["ollama", "lmstudio"])
def test_without_a_model_name_the_insights_are_unconfigured(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    built = build_insight_provider(_settings(monkeypatch, AI_PROVIDER=provider))
    assert isinstance(built, UnconfiguredInsightProvider)
    assert built.insight_for("lead_time", {})["reason"] == "AI_NOT_CONFIGURED"


def test_the_model_of_ollama_is_used_when_it_is_the_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(
        monkeypatch, AI_PROVIDER="ollama", OLLAMA_MODEL="phi3.5", LM_STUDIO_MODEL="other"
    )
    built = build_insight_provider(settings)
    assert isinstance(built, ModelInsightProvider)
    assert built.info() == {"provider": "ollama", "model": "phi3.5", "prompt_version": "1"}


def test_the_model_of_lm_studio_is_used_when_it_is_the_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(
        monkeypatch, AI_PROVIDER="lmstudio", LM_STUDIO_MODEL="qwen", OLLAMA_MODEL="other"
    )
    built = build_insight_provider(settings)
    assert isinstance(built, ModelInsightProvider)
    assert built.info() == {"provider": "lmstudio", "model": "qwen", "prompt_version": "1"}


def test_the_clients_are_the_adapters_of_the_selected_provider() -> None:
    assert OllamaModelClient("http://h:1", "m").provider == "ollama"
    assert LMStudioModelClient("http://h:1", "m").provider == "lmstudio"
