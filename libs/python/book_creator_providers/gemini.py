"""Google Gemini provider implementation."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict

from google import genai

from .base import LLMProvider, ProviderCapabilities, ProviderRequest, ProviderResponse
from .config import ProviderConfig
from .exceptions import ProviderResponseError
from .pricing import estimate_cost


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client = genai.GenerativeModel(model_name=config.model, api_key=config.api_key)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_json_mode=True,
            max_input_tokens=None,
            max_output_tokens=self._config.settings.max_output_tokens,
            supports_tool_calls=True,
            supports_thinking=True,
            supports_thought_summaries=True,
        )

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        contents: list[Any] = []
        if request.system_prompt:
            contents.append(request.system_prompt)
        contents.append(request.prompt)

        temperature = (
            request.temperature
            if request.temperature is not None
            else self._config.settings.temperature
        )

        generation_config: Dict[str, Any] = {"temperature": temperature}

        if request.top_p is not None:
            generation_config["top_p"] = request.top_p
        elif self._config.settings.top_p is not None:
            generation_config["top_p"] = self._config.settings.top_p

        max_output = (
            request.max_output_tokens
            if request.max_output_tokens is not None
            else self._config.settings.max_output_tokens
        )
        if max_output:
            generation_config["max_output_tokens"] = max_output

        if request.json_schema:
            generation_config["response_mime_type"] = "application/json"
            generation_config["response_schema"] = request.json_schema

        thinking_budget = (
            request.thinking_budget
            if request.thinking_budget is not None
            else self._config.settings.thinking_budget
        )
        include_thoughts = (
            request.include_thoughts
            if request.include_thoughts is not None
            else self._config.settings.include_thoughts
        )

        thinking_config: Dict[str, Any] = {}
        if thinking_budget is not None:
            thinking_config["thinking_budget"] = thinking_budget
            thinking_config["thinkingBudget"] = thinking_budget
        if include_thoughts:
            thinking_config["include_thoughts"] = True
            thinking_config["includeThoughts"] = True
        if thinking_config:
            generation_config["thinking_config"] = thinking_config

        start = time.perf_counter()
        # google-genai SDK is synchronous; run in thread to avoid blocking event loop.
        response = await asyncio.to_thread(
            self._client.generate_content,
            contents,
            generation_config=generation_config,
        )
        latency_ms = (time.perf_counter() - start) * 1000

        try:
            text = response.text or ""
        except AttributeError as err:
            raise ProviderResponseError("Gemini response missing text content") from err

        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        completion_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
        cost_usd = estimate_cost(
            provider=self._config.name,
            model=self._config.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        return ProviderResponse(
            text=text,
            raw=response,
            model=self._config.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )
