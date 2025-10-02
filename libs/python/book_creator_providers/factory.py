"""Factory utilities for instantiating providers."""

from __future__ import annotations

from typing import Dict, Type

from .base import LLMProvider
from .config import ProviderConfig, load_provider_config
from .exceptions import ProviderConfigError
from .gemini import GeminiProvider
from .mock import MockProvider
from .openai import OpenAIProvider

PROVIDER_MAP: Dict[str, Type[LLMProvider]] = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "mock": MockProvider,
}


class ProviderFactory:
    """Factory for creating providers based on configuration."""

    @staticmethod
    def create(config: ProviderConfig | None = None) -> LLMProvider:
        if config is None:
            config = load_provider_config()
        provider_cls = PROVIDER_MAP.get(config.name.lower())
        if provider_cls is None:
            raise ProviderConfigError(f"Unknown provider: {config.name}")
        return provider_cls(config)
