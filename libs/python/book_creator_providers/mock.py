"""Deterministic mock provider for tests and offline development."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from .base import LLMProvider, ProviderCapabilities, ProviderRequest, ProviderResponse
from .config import ProviderConfig, ProviderSettings

DEFAULT_TEXT = "Mock response generated for testing."


@dataclass
class MockProvider(LLMProvider):
    name: str = "mock"
    _config: ProviderConfig | None = None

    def __init__(self, config: ProviderConfig | None = None) -> None:
        if config is None:
            settings = ProviderSettings(temperature=0.1, json_mode=False)
            config = ProviderConfig(name="mock", api_key="mock", model="mock", settings=settings)
        self._config = config

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_json_mode=True,
            max_input_tokens=32000,
            max_output_tokens=2000,
            supports_tool_calls=False,
        )

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        payload: Any
        if request.json_schema:
            payload = {"message": DEFAULT_TEXT, "echo": request.prompt[:50]}
            text = json.dumps(payload)
        else:
            text = f"{DEFAULT_TEXT}\nPrompt: {request.prompt[:80]}"
            payload = text
        return ProviderResponse(
            text=text,
            raw={"mock": True, "payload": payload},
            model="mock",
            prompt_tokens=len(request.prompt.split()),
            completion_tokens=len(text.split()),
            cost_usd=0.0,
            latency_ms=1.0,
        )
