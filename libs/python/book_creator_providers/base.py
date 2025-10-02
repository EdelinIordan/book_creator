"""Core interfaces and dataclasses for provider interactions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, MutableMapping, Optional


@dataclass(slots=True)
class ProviderRequest:
    """Normalized request passed to providers."""

    prompt: str
    system_prompt: str | None = None
    json_schema: Mapping[str, Any] | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    top_p: float | None = None
    reasoning_effort: str | None = None
    verbosity: str | None = None
    thinking_budget: int | None = None
    include_thoughts: bool | None = None
    metadata: MutableMapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderResponse:
    """Standard response returned by providers."""

    text: str
    raw: Any
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float | None = None
    latency_ms: float | None = None
    received_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class ProviderCapabilities:
    """Capability flags used when choosing a provider."""

    supports_json_mode: bool = False
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    supports_tool_calls: bool = False
    supports_reasoning_effort: bool = False
    supports_verbosity: bool = False
    supports_thinking: bool = False
    supports_thought_summaries: bool = False


class LLMProvider(ABC):
    """Abstract base class implemented by concrete providers."""

    name: str

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return capability metadata."""

    @abstractmethod
    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Generate text or JSON response for the provided prompt."""

    def generate_sync(self, request: ProviderRequest) -> ProviderResponse:
        """Blocking helper for contexts without async support."""

        import asyncio

        return asyncio.run(self.generate(request))
