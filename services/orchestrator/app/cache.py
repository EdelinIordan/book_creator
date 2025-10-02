"""Lightweight caching layer for provider responses."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from typing import Any, Dict, Optional

from book_creator_providers import ProviderConfig
from book_creator_providers.base import LLMProvider, ProviderRequest, ProviderResponse

from .context import summarise_prompt

try:  # pragma: no cover - redis optional
    from redis.asyncio import Redis
except ModuleNotFoundError:  # pragma: no cover - fallback when redis is unavailable
    Redis = None


class StageCache:
    """Cache provider responses in Redis with in-memory fallback."""

    def __init__(self) -> None:
        self._ttl_seconds = int(os.getenv("LLM_CACHE_TTL_SECONDS", "900"))
        self._prompt_limit = int(os.getenv("CONTEXT_TOKEN_LIMIT", "12000"))
        self._redis: Optional[Redis] = None
        redis_url = os.getenv("REDIS_URL")
        if Redis and redis_url:
            try:
                self._redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
            except Exception:  # pragma: no cover - fallback when connection fails
                self._redis = None
        self._local: Dict[str, tuple[dict[str, Any], float]] = {}
        self._lock = asyncio.Lock()

    async def generate(
        self,
        provider_config: ProviderConfig,
        provider: LLMProvider,
        request: ProviderRequest,
        stage_name: str,
    ) -> ProviderResponse:
        original_prompt = request.prompt
        cache_key = self._build_key(provider_config, request, stage_name, original_prompt)

        cached = await self._get(cache_key)
        if cached is not None:
            return self._decode_response(cached)

        trimmed_prompt, was_trimmed = summarise_prompt(
            original_prompt, token_limit=self._prompt_limit
        )
        if was_trimmed:
            request.prompt = trimmed_prompt
            request.metadata.setdefault("trimming", {})
            request.metadata["trimming"] = {
                "applied": True,
                "limit_tokens": self._prompt_limit,
                "original_hash": self._hash_text(original_prompt),
            }
        else:
            request.metadata.setdefault("trimming", {"applied": False})

        response = await provider.generate(request)
        await self._set(cache_key, self._encode_response(response))
        return response

    async def _get(self, key: str) -> Optional[dict[str, Any]]:
        if self._redis is not None:
            try:
                payload = await self._redis.get(key)
                if payload:
                    return json.loads(payload)
            except Exception:  # pragma: no cover - connection issues fall back silently
                pass
        entry = self._local.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if expires_at < time.time():
            self._local.pop(key, None)
            return None
        return value

    async def _set(self, key: str, value: dict[str, Any]) -> None:
        if self._redis is not None:
            try:
                await self._redis.set(key, json.dumps(value, ensure_ascii=False), ex=self._ttl_seconds)
                return
            except Exception:  # pragma: no cover - fallback on write failure
                pass
        self._local[key] = (value, time.time() + self._ttl_seconds)

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _build_key(
        self,
        provider_config: ProviderConfig,
        request: ProviderRequest,
        stage_name: str,
        original_prompt: str,
    ) -> str:
        payload: dict[str, Any] = {
            "provider": provider_config.name,
            "model": provider_config.model,
            "stage": stage_name,
            "prompt": original_prompt,
            "system": request.system_prompt,
            "json_schema": self._normalise(request.json_schema),
            "temperature": request.temperature,
            "max_output_tokens": request.max_output_tokens,
            "top_p": request.top_p,
            "reasoning_effort": request.reasoning_effort,
            "verbosity": request.verbosity,
            "thinking_budget": request.thinking_budget,
            "include_thoughts": request.include_thoughts,
        }
        serialised = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return self._hash_text(serialised)

    @staticmethod
    def _normalise(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        try:
            return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False))
        except TypeError:  # pragma: no cover - fallback for non-serialisable structures
            return str(value)

    def _encode_response(self, response: ProviderResponse) -> dict[str, Any]:
        return {
            "text": response.text,
            "model": response.model,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "cost_usd": response.cost_usd,
            "latency_ms": response.latency_ms,
        }

    def _decode_response(self, payload: dict[str, Any]) -> ProviderResponse:
        return ProviderResponse(
            text=payload.get("text", ""),
            raw={"cached": True},
            model=payload.get("model", "unknown"),
            prompt_tokens=int(payload.get("prompt_tokens") or 0),
            completion_tokens=int(payload.get("completion_tokens") or 0),
            cost_usd=payload.get("cost_usd"),
            latency_ms=payload.get("latency_ms") or 0.0,
        )


_STAGE_CACHE = StageCache()


async def generate_with_cache(
    provider_config: ProviderConfig,
    provider: LLMProvider,
    request: ProviderRequest,
    stage_name: str,
) -> ProviderResponse:
    """Generate a provider response using the shared cache."""

    return await _STAGE_CACHE.generate(provider_config, provider, request, stage_name)


__all__ = ["generate_with_cache"]
