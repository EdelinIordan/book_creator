"""Tests for provider configuration loading."""

import os

import pytest

from book_creator_providers import ProviderConfig, ProviderSettings, load_provider_config
from book_creator_providers.config import DEFAULT_PROVIDER, PROVIDER_ENV_VAR


@pytest.fixture(autouse=True)
def clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("OPENAI_") or key.startswith("GEMINI_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv(PROVIDER_ENV_VAR, raising=False)


def test_load_openai_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PROVIDER_ENV_VAR, "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1")
    cfg = load_provider_config()
    assert cfg.name == "openai"
    assert cfg.api_key == "key"


def test_missing_variables_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PROVIDER_ENV_VAR, "gemini")
    with pytest.raises(Exception):
        load_provider_config()


def test_custom_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MYPROV_API_KEY", "abc")
    monkeypatch.setenv("MYPROV_MODEL", "model")
    cfg = load_provider_config(prefix="myprov")
    assert cfg.name == "myprov"
    assert cfg.settings.temperature == 0.4
