"""Static pricing tables and helpers for estimating provider cost."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping


@dataclass(frozen=True)
class _TokenPricing:
    """Per-model pricing expressed as USD per one million tokens."""

    input_per_million: float
    output_per_million: float


_OPENAI_PRICING: Mapping[str, _TokenPricing] = {
    "gpt-5": _TokenPricing(input_per_million=1.25, output_per_million=10.0),
    "gpt-5-mini": _TokenPricing(input_per_million=0.25, output_per_million=2.0),
    "gpt-5-nano": _TokenPricing(input_per_million=0.05, output_per_million=0.4),
    "gpt-5-chat-latest": _TokenPricing(input_per_million=1.25, output_per_million=10.0),
}

_GEMINI_PRICING: Mapping[str, _TokenPricing] = {
    "gemini-2.5-pro": _TokenPricing(input_per_million=1.25, output_per_million=10.0),
    "gemini-2.5-flash": _TokenPricing(input_per_million=0.30, output_per_million=2.5),
}

_PROVIDER_PRICING: Dict[str, Mapping[str, _TokenPricing]] = {
    "openai": _OPENAI_PRICING,
    "gemini": _GEMINI_PRICING,
}


def estimate_cost(
    provider: str,
    model: str,
    prompt_tokens: int | float | None,
    completion_tokens: int | float | None,
) -> float | None:
    """Approximate cost in USD for a provider response.

    Args:
        provider: Provider identifier ("openai", "gemini", "mock", etc.).
        model: Concrete model name, used to select the right pricing row.
        prompt_tokens: Number of prompt/input tokens billed for the request.
        completion_tokens: Number of completion/output tokens billed.

    Returns:
        Estimated USD cost, or ``None`` when pricing is unknown.
    """

    provider_key = (provider or "").lower()
    if provider_key == "mock":
        return 0.0

    model_key = (model or "").lower()
    table = _PROVIDER_PRICING.get(provider_key)
    if not table:
        return None

    pricing = table.get(model_key)
    if pricing is None:
        return None

    prompt_value = max(float(prompt_tokens or 0.0), 0.0)
    completion_value = max(float(completion_tokens or 0.0), 0.0)

    cost = (
        (prompt_value * pricing.input_per_million)
        + (completion_value * pricing.output_per_million)
    ) / 1_000_000.0

    # Normalise to 6 decimal places to avoid noisy floating point representations.
    return round(cost, 6)


__all__ = ["estimate_cost"]
