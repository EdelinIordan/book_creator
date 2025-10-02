"""Research prompt generation workflow leveraging provider abstraction."""

from __future__ import annotations

import json
from dataclasses import dataclass

from book_creator_providers import LLMProvider, ProviderConfig, ProviderFactory, ProviderRequest
from book_creator_providers.exceptions import ProviderResponseError
from book_creator_schemas import BookStage
from pydantic import BaseModel, Field

from ..cache import generate_with_cache
from ..models import ProviderOverride
from ..providers import resolve_provider_config
from .prompts import (
    RESEARCH_BATCH_PROMPT,
    RESEARCH_CRITIQUE_PROMPT,
    RESEARCH_REWRITE_PROMPT,
    RESEARCH_SYSTEM_PROMPT,
)


class ResearchPromptDraft(BaseModel):
    """Single research task returned by the LLM."""

    focus_summary: str = Field(..., min_length=2, max_length=400)
    focus_subchapters: list[str] = Field(default_factory=list)
    prompt_text: str = Field(..., min_length=5)
    desired_sources: list[str] = Field(default_factory=list)
    additional_notes: str | None = Field(default=None, max_length=600)


class ResearchPromptBatch(BaseModel):
    """Container for three research prompts."""

    prompts: list[ResearchPromptDraft] = Field(..., min_items=1, max_items=5)


@dataclass
class ResearchPromptResult:
    """Return value for research prompt generation."""

    batch: ResearchPromptBatch
    critique: str | None
    cost_usd: float | None


async def generate_research_prompts(
    synopsis: str,
    structure_summary: str,
    guidelines: str,
    run_override: ProviderOverride | None,
    stage_override: ProviderOverride | None,
) -> ResearchPromptResult:
    """Generate research prompts using proposal/critique/rewrite loop."""

    effective_override = _merge_overrides(stage_override, run_override)
    provider_config = resolve_provider_config(effective_override)
    provider: LLMProvider = ProviderFactory.create(provider_config)

    total_cost = 0.0
    cost_samples = 0

    def _record_cost(response) -> None:
        nonlocal total_cost, cost_samples
        if response.cost_usd is not None:
            total_cost += response.cost_usd
            cost_samples += 1

    initial_response = await _request_batch(
        provider,
        provider_config,
        RESEARCH_BATCH_PROMPT.format(
            synopsis=synopsis.strip(),
            structure_summary=structure_summary.strip(),
            guidelines=guidelines.strip() or "No additional guidance provided.",
        ),
        effective_override,
    )
    _record_cost(initial_response)
    initial = _parse_batch(initial_response.text)

    critique_response = await _request_text(
        provider,
        provider_config,
        RESEARCH_CRITIQUE_PROMPT.format(
            batch_json=json.dumps(initial.model_dump(mode="json"), ensure_ascii=False)
        ),
        effective_override,
    )
    _record_cost(critique_response)

    improved_response = await _request_batch(
        provider,
        provider_config,
        RESEARCH_REWRITE_PROMPT.format(
            batch_json=json.dumps(initial.model_dump(mode="json"), ensure_ascii=False),
            critique=critique_response.text,
        ),
        effective_override,
    )
    _record_cost(improved_response)
    improved = _parse_batch(improved_response.text)

    return ResearchPromptResult(
        batch=improved,
        critique=critique_response.text if critique_response.text else None,
        cost_usd=total_cost if cost_samples else None,
    )


async def _request_batch(
    provider: LLMProvider,
    provider_config: ProviderConfig,
    prompt: str,
    override: ProviderOverride | None,
):
    request = ProviderRequest(
        prompt=prompt,
        system_prompt=RESEARCH_SYSTEM_PROMPT,
        json_schema=ResearchPromptBatch.model_json_schema(),
        temperature=_resolve_param("temperature", override, 0.4),
        max_output_tokens=_resolve_param("max_output_tokens", override),
        top_p=_resolve_param("top_p", override),
        reasoning_effort=_resolve_param("reasoning_effort", override),
        verbosity=_resolve_param("verbosity", override),
        thinking_budget=_resolve_param("thinking_budget", override),
        include_thoughts=_resolve_param("include_thoughts", override),
        metadata={"stage": BookStage.RESEARCH.value},
    )
    return await generate_with_cache(provider_config, provider, request, BookStage.RESEARCH.value)


async def _request_text(
    provider: LLMProvider,
    provider_config: ProviderConfig,
    prompt: str,
    override: ProviderOverride | None,
):
    request = ProviderRequest(
        prompt=prompt,
        system_prompt=None,
        temperature=_resolve_param("temperature", override, 0.3),
        max_output_tokens=_resolve_param("max_output_tokens", override),
        top_p=_resolve_param("top_p", override),
        reasoning_effort=_resolve_param("reasoning_effort", override),
        verbosity=_resolve_param("verbosity", override),
        thinking_budget=_resolve_param("thinking_budget", override),
        include_thoughts=_resolve_param("include_thoughts", override),
        metadata={"stage": BookStage.RESEARCH.value, "agent": "critic"},
    )
    return await generate_with_cache(provider_config, provider, request, BookStage.RESEARCH.value)


def _parse_batch(payload: str) -> ResearchPromptBatch:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ProviderResponseError("Research prompt response was not valid JSON") from exc
    return ResearchPromptBatch.model_validate(data)


def _resolve_param(name: str, override: ProviderOverride | None, default=None):
    if override is None:
        return default
    value = getattr(override, name, None)
    return value if value is not None else default


def _merge_overrides(
    stage_override: ProviderOverride | None, run_override: ProviderOverride | None
) -> ProviderOverride | None:
    if stage_override is None:
        return run_override
    if run_override is None:
        return stage_override
    return ProviderOverride(
        name=stage_override.name or run_override.name,
        model=stage_override.model or run_override.model,
        temperature=
            stage_override.temperature
            if stage_override.temperature is not None
            else run_override.temperature,
        max_output_tokens=
            stage_override.max_output_tokens
            if stage_override.max_output_tokens is not None
            else run_override.max_output_tokens,
        json_mode=
            stage_override.json_mode
            if stage_override.json_mode is not None
            else run_override.json_mode,
        top_p=
            stage_override.top_p
            if stage_override.top_p is not None
            else run_override.top_p,
        reasoning_effort=
            stage_override.reasoning_effort
            if stage_override.reasoning_effort is not None
            else run_override.reasoning_effort,
        verbosity=
            stage_override.verbosity
            if stage_override.verbosity is not None
            else run_override.verbosity,
        thinking_budget=
            stage_override.thinking_budget
            if stage_override.thinking_budget is not None
            else run_override.thinking_budget,
        include_thoughts=
            stage_override.include_thoughts
            if stage_override.include_thoughts is not None
            else run_override.include_thoughts,
    )
