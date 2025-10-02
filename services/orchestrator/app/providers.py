"""Utilities for working with provider configurations inside the orchestrator."""

from __future__ import annotations

import os

from book_creator_providers import ProviderConfig, ProviderSettings, load_provider_config

from .models import ProviderOverride


def resolve_provider_config(override: ProviderOverride | None) -> ProviderConfig:
    provider_name = override.name if override and override.name else os.getenv("LLM_PROVIDER", "mock")

    if provider_name and provider_name.lower() == "mock":
        return ProviderConfig(
            name="mock",
            api_key="mock",
            model="mock",
            settings=ProviderSettings(),
        )

    if override and override.name:
        config = load_provider_config(prefix=override.name)
    else:
        config = load_provider_config()

    update_kwargs = {}
    if override:
        if override.model:
            update_kwargs["model"] = override.model

        settings_updates = {}
        if override.temperature is not None:
            settings_updates["temperature"] = override.temperature
        if override.max_output_tokens is not None:
            settings_updates["max_output_tokens"] = override.max_output_tokens
        if override.top_p is not None:
            settings_updates["top_p"] = override.top_p
        if override.json_mode is not None:
            settings_updates["json_mode"] = override.json_mode
        if override.reasoning_effort is not None:
            settings_updates["reasoning_effort"] = override.reasoning_effort
        if override.verbosity is not None:
            settings_updates["verbosity"] = override.verbosity
        if override.thinking_budget is not None:
            settings_updates["thinking_budget"] = override.thinking_budget
        if override.include_thoughts is not None:
            settings_updates["include_thoughts"] = override.include_thoughts

        if settings_updates:
            update_kwargs["settings"] = config.settings.model_copy(update=settings_updates)

    if update_kwargs:
        config = config.model_copy(update=update_kwargs)

    return config
