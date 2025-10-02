"""OpenAI ChatGPT provider implementation."""

from __future__ import annotations

import time
from typing import Any, Dict, List

from openai import AsyncOpenAI

from .base import LLMProvider, ProviderCapabilities, ProviderRequest, ProviderResponse
from .config import ProviderConfig
from .exceptions import ProviderResponseError
from .pricing import estimate_cost


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client = AsyncOpenAI(api_key=config.api_key)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_json_mode=True,
            max_input_tokens=None,
            max_output_tokens=self._config.settings.max_output_tokens,
            supports_tool_calls=True,
            supports_reasoning_effort=True,
            supports_verbosity=True,
        )

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        messages: List[Dict[str, Any]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        temperature = (
            request.temperature
            if request.temperature is not None
            else self._config.settings.temperature
        )

        params: Dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "temperature": temperature,
        }

        if request.top_p is not None:
            params["top_p"] = request.top_p
        elif self._config.settings.top_p is not None:
            params["top_p"] = self._config.settings.top_p

        max_output = (
            request.max_output_tokens
            if request.max_output_tokens is not None
            else self._config.settings.max_output_tokens
        )
        if max_output:
            params["max_output_tokens"] = max_output

        if request.json_schema:
            params["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "structured", "schema": request.json_schema},
            }
        elif self._config.settings.json_mode:
            params["response_format"] = {"type": "json_object"}

        reasoning_effort = (
            request.reasoning_effort
            if request.reasoning_effort is not None
            else self._config.settings.reasoning_effort
        )
        if reasoning_effort:
            params["reasoning_effort"] = reasoning_effort

        verbosity = (
            request.verbosity
            if request.verbosity is not None
            else self._config.settings.verbosity
        )
        if verbosity:
            params["verbosity"] = verbosity

        start = time.perf_counter()
        response = await self._client.chat.completions.create(**params)
        latency_ms = (time.perf_counter() - start) * 1000

        try:
            choice = response.choices[0].message
            text = choice.content or ""
        except (IndexError, AttributeError) as err:
            raise ProviderResponseError("OpenAI response missing content") from err

        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        cost_usd = estimate_cost(
            provider=self._config.name,
            model=response.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        return ProviderResponse(
            text=text,
            raw=response,
            model=response.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )
