"""Configuration models and helpers for provider selection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, ValidationError

PROVIDER_ENV_VAR = "LLM_PROVIDER"
DEFAULT_PROVIDER = "gemini"


class ProviderSettings(BaseModel):
    """Per-call default parameters."""

    temperature: float = Field(0.4, ge=0, le=2)
    max_output_tokens: int | None = Field(None, ge=16)
    top_p: float | None = Field(None, ge=0, le=1)
    json_mode: bool = Field(False)
    reasoning_effort: str | None = Field(
        None, description="Default reasoning effort parameter for OpenAI GPT-5 family"
    )
    verbosity: str | None = Field(
        None, description="Default verbosity hint for OpenAI GPT-5 family"
    )
    thinking_budget: int | None = Field(
        None,
        description=(
            "Default thinking token budget for Gemini 2.5 models; use -1 for dynamic thinking"
        ),
    )
    include_thoughts: bool = Field(
        False, description="Whether Gemini responses should include thought summaries by default"
    )


class ProviderConfig(BaseModel):
    """Configuration for a single provider instance."""

    name: str
    api_key: str
    model: str
    settings: ProviderSettings = Field(default_factory=ProviderSettings)

    class Config:
        frozen = True


def load_provider_config(prefix: str | None = None) -> ProviderConfig:
    """Load configuration from environment variables.

    Args:
        prefix: Optional prefix for environment variables (default uses provider name).

    Environment variables used (assuming prefix "OPENAI"):
        OPENAI_API_KEY
        OPENAI_MODEL
        OPENAI_TEMPERATURE (optional)
        OPENAI_MAX_OUTPUT_TOKENS (optional)
        OPENAI_TOP_P (optional)
        OPENAI_JSON_MODE (optional boolean)

    Returns:
        ProviderConfig object populated from environment variables.

    Raises:
        ValidationError: If required variables are missing or invalid.
    """

    provider_name = (prefix or os.getenv(PROVIDER_ENV_VAR, DEFAULT_PROVIDER)).upper()
    env_prefix = provider_name

    def read_env(key: str, default: Any | None = None) -> Any:
        return os.getenv(f"{env_prefix}_{key}", default)

    def parse_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"true", "1", "yes", "on"}

    api_key = read_env("API_KEY")
    model = read_env("MODEL")
    if not api_key or not model:
        raise ValidationError(
            [
                {
                    "loc": ("api_key",),
                    "msg": "API key or model not configured",
                    "type": "value_error",
                }
            ],
            ProviderConfig,
        )

    temperature = float(read_env("TEMPERATURE", 0.4))
    max_output_raw = read_env("MAX_OUTPUT_TOKENS")
    max_output_tokens = None
    if max_output_raw not in (None, ""):
        try:
            parsed_max = int(str(max_output_raw).strip())
            max_output_tokens = parsed_max if parsed_max > 0 else None
        except (TypeError, ValueError) as exc:  # pragma: no cover - environment misconfiguration
            raise ValidationError(
                [
                    {
                        "loc": ("settings", "max_output_tokens"),
                        "msg": "MAX_OUTPUT_TOKENS must be a positive integer",
                        "type": "value_error",
                    }
                ],
                ProviderConfig,
            ) from exc

    top_p_raw = read_env("TOP_P", "")
    try:
        top_p = float(top_p_raw) if str(top_p_raw).strip() else None
    except ValueError as exc:  # pragma: no cover - environment misconfiguration
        raise ValidationError(
            [
                {
                    "loc": ("settings", "top_p"),
                    "msg": "TOP_P must be a float between 0 and 1",
                    "type": "value_error",
                }
            ],
            ProviderConfig,
        ) from exc

    reasoning_effort = read_env("REASONING_EFFORT")
    reasoning_effort = reasoning_effort.strip() if isinstance(reasoning_effort, str) else reasoning_effort
    if isinstance(reasoning_effort, str) and not reasoning_effort:
        reasoning_effort = None

    verbosity = read_env("VERBOSITY")
    verbosity = verbosity.strip() if isinstance(verbosity, str) else verbosity
    if isinstance(verbosity, str) and not verbosity:
        verbosity = None

    thinking_budget_raw = read_env("THINKING_BUDGET")
    thinking_budget = None
    if thinking_budget_raw not in (None, ""):
        try:
            thinking_budget = int(str(thinking_budget_raw).strip())
        except (TypeError, ValueError) as exc:  # pragma: no cover - environment misconfiguration
            raise ValidationError(
                [
                    {
                        "loc": ("settings", "thinking_budget"),
                        "msg": "THINKING_BUDGET must be an integer",
                        "type": "value_error",
                    }
                ],
                ProviderConfig,
            ) from exc

    include_thoughts = parse_bool(read_env("INCLUDE_THOUGHTS", False))

    settings = ProviderSettings(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        top_p=top_p,
        json_mode=parse_bool(read_env("JSON_MODE", "false")),
        reasoning_effort=reasoning_effort,
        verbosity=verbosity,
        thinking_budget=thinking_budget,
        include_thoughts=include_thoughts,
    )

    return ProviderConfig(name=provider_name.lower(), api_key=api_key, model=model, settings=settings)
