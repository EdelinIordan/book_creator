"""Structure generation workflow orchestrated via providers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

from book_creator_providers import LLMProvider, ProviderConfig, ProviderFactory, ProviderRequest
from book_creator_providers.exceptions import ProviderResponseError
from book_creator_schemas import BookStage
from book_creator_schemas.models.book import BookStructure

from ..cache import generate_with_cache
from ..models import ProviderOverride
from ..providers import resolve_provider_config
from .prompts import (
    FINAL_SUMMARY_PROMPT,
    STRUCTURE_CRITIQUE_PROMPT,
    STRUCTURE_IMPROVEMENT_PROMPT,
    STRUCTURE_PROPOSAL_PROMPT,
    STRUCTURE_SYSTEM_PROMPT,
)

BOOK_STRUCTURE_SCHEMA = BookStructure.model_json_schema()


@dataclass
class StructureGenerationResult:
    structure: BookStructure
    summary_text: str
    critiques: List[str]
    cost_usd: float | None


async def generate_structure(
    idea_text: str,
    context: str,
    run_override: ProviderOverride | None,
    stage_override: ProviderOverride | None,
) -> StructureGenerationResult:
    """Run the multi-agent loop to produce a validated book structure."""

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

    # 1. Initial proposal
    initial_response = await _request_structure(
        provider,
        provider_config,
        STRUCTURE_PROPOSAL_PROMPT.format(idea=idea_text.strip(), context=context.strip()),
        effective_override,
    )
    _record_cost(initial_response)
    structure = _parse_structure(initial_response.text)
    critiques: List[str] = []

    current_structure_json = json.dumps(
        structure.model_dump(mode="json"), ensure_ascii=False
    )

    # 2–6. Critique / improvement loops (three cycles -> 6 agents)
    for _ in range(3):
        critique = await _request_text(
            provider,
            provider_config,
            STRUCTURE_CRITIQUE_PROMPT.format(structure_json=current_structure_json),
            effective_override,
        )
        _record_cost(critique)
        critiques.append(critique.text.strip())

        improved = await _request_structure(
            provider,
            provider_config,
            STRUCTURE_IMPROVEMENT_PROMPT.format(
                structure_json=current_structure_json, critique=critique.text
            ),
            effective_override,
        )
        _record_cost(improved)
        structure = _parse_structure(improved.text)
        current_structure_json = json.dumps(
            structure.model_dump(mode="json"), ensure_ascii=False
        )

    # 7. Final summary agent
    summary = await _request_text(
        provider,
        provider_config,
        FINAL_SUMMARY_PROMPT.format(structure_json=current_structure_json),
        effective_override,
    )
    _record_cost(summary)

    return StructureGenerationResult(
        structure=structure,
        summary_text=summary.text,
        critiques=critiques,
        cost_usd=total_cost if cost_samples else None,
    )


async def _request_structure(
    provider: LLMProvider,
    provider_config: ProviderConfig,
    prompt: str,
    override: ProviderOverride | None,
):
    request = ProviderRequest(
        prompt=prompt,
        system_prompt=STRUCTURE_SYSTEM_PROMPT,
        json_schema=BOOK_STRUCTURE_SCHEMA,
        temperature=_resolve_param("temperature", override),
        max_output_tokens=_resolve_param("max_output_tokens", override),
        top_p=_resolve_param("top_p", override),
        reasoning_effort=_resolve_param("reasoning_effort", override),
        verbosity=_resolve_param("verbosity", override),
        thinking_budget=_resolve_param("thinking_budget", override),
        include_thoughts=_resolve_param("include_thoughts", override),
        metadata={"stage": BookStage.STRUCTURE.value},
    )
    return await generate_with_cache(provider_config, provider, request, BookStage.STRUCTURE.value)


async def _request_text(
    provider: LLMProvider,
    provider_config: ProviderConfig,
    prompt: str,
    override: ProviderOverride | None,
):
    request = ProviderRequest(
        prompt=prompt,
        system_prompt=None,
        temperature=_resolve_param("temperature", override, default=0.2),
        max_output_tokens=_resolve_param("max_output_tokens", override),
        top_p=_resolve_param("top_p", override),
        reasoning_effort=_resolve_param("reasoning_effort", override),
        verbosity=_resolve_param("verbosity", override),
        thinking_budget=_resolve_param("thinking_budget", override),
        include_thoughts=_resolve_param("include_thoughts", override),
        metadata={"stage": BookStage.STRUCTURE.value, "agent": "critic"},
    )
    return await generate_with_cache(provider_config, provider, request, BookStage.STRUCTURE.value)


def _parse_structure(payload: str) -> BookStructure:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ProviderResponseError("Structure response was not valid JSON") from exc
    return BookStructure.model_validate(data)


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
