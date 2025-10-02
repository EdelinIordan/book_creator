"""Orchestrates the fact mapping tri-agent workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from book_creator_providers import LLMProvider, ProviderConfig, ProviderFactory, ProviderRequest
from book_creator_providers.exceptions import ProviderResponseError
from book_creator_schemas import BookStage
from book_creator_schemas.models.book import (
    BookStructure,
    FactMappingBatch,
    ResearchFactCandidate,
    SubchapterFactCoverage,
)

from ..cache import generate_with_cache
from ..models import ProviderOverride
from ..providers import resolve_provider_config
from .prompts import (
    FACT_MAPPING_CRITIQUE_PROMPT,
    FACT_MAPPING_FINAL_PROMPT,
    FACT_MAPPING_PROPOSAL_PROMPT,
    FACT_MAPPING_SYSTEM_PROMPT,
)

FACT_MAPPING_SCHEMA = FactMappingBatch.model_json_schema()


@dataclass
class FactMappingResult:
    """Container returned to the flow with final mapping and critique."""

    batch: FactMappingBatch
    critique: str | None
    cost_usd: float | None


async def generate_fact_mapping(
    payload: dict[str, Any],
    run_override: ProviderOverride | None,
    stage_override: ProviderOverride | None,
) -> FactMappingResult:
    """Execute the three-agent fact mapping sequence."""

    effective_override = _merge_overrides(stage_override, run_override)
    provider_config = resolve_provider_config(effective_override)
    provider: LLMProvider = ProviderFactory.create(provider_config)

    structure = BookStructure.model_validate(payload.get("structure") or {})
    candidates = [
        ResearchFactCandidate.model_validate(item)
        for item in payload.get("candidates", [])
    ]

    structure_json = json.dumps(structure.model_dump(mode="json"), ensure_ascii=False)
    candidate_json = json.dumps(
        [candidate.model_dump(mode="json") for candidate in candidates], ensure_ascii=False
    )

    # M1 – Fact Selector
    total_cost = 0.0
    cost_samples = 0

    def _record_cost(response) -> None:
        nonlocal total_cost, cost_samples
        if response.cost_usd is not None:
            total_cost += response.cost_usd
            cost_samples += 1

    proposal_response = await _request_mapping(
        provider,
        provider_config,
        prompt=FACT_MAPPING_PROPOSAL_PROMPT.format(
            structure_json=structure_json,
            candidate_json=candidate_json,
        ),
        override=effective_override,
    )
    _record_cost(proposal_response)
    mapping = _parse_mapping(proposal_response.text)

    # M2 – Fact Critic
    critique_response = await _request_text(
        provider,
        provider_config,
        prompt=FACT_MAPPING_CRITIQUE_PROMPT.format(
            mapping_json=json.dumps(mapping.model_dump(mode="json"), ensure_ascii=False)
        ),
        override=effective_override,
    )
    _record_cost(critique_response)
    critique_text = critique_response.text.strip()

    # M3 – Fact Implementer
    final_response = await _request_mapping(
        provider,
        provider_config,
        prompt=FACT_MAPPING_FINAL_PROMPT.format(
            structure_json=structure_json,
            candidate_json=candidate_json,
            mapping_json=json.dumps(mapping.model_dump(mode="json"), ensure_ascii=False),
            critique_text=critique_text,
        ),
        override=effective_override,
    )
    _record_cost(final_response)
    final_mapping = _parse_mapping(final_response.text)
    final_mapping.coverage = _build_coverage(structure, final_mapping)

    return FactMappingResult(
        batch=final_mapping,
        critique=critique_text or None,
        cost_usd=total_cost if cost_samples else None,
    )


async def _request_mapping(
    provider: LLMProvider,
    provider_config: ProviderConfig,
    prompt: str,
    override: ProviderOverride | None,
):
    request = ProviderRequest(
        prompt=prompt,
        system_prompt=FACT_MAPPING_SYSTEM_PROMPT,
        json_schema=FACT_MAPPING_SCHEMA,
        temperature=_resolve_param("temperature", override, default=0.2),
        max_output_tokens=_resolve_param("max_output_tokens", override),
        top_p=_resolve_param("top_p", override),
        reasoning_effort=_resolve_param("reasoning_effort", override),
        verbosity=_resolve_param("verbosity", override),
        thinking_budget=_resolve_param("thinking_budget", override),
        include_thoughts=_resolve_param("include_thoughts", override),
        metadata={"stage": BookStage.FACT_MAPPING.value},
    )
    return await generate_with_cache(provider_config, provider, request, BookStage.FACT_MAPPING.value)


async def _request_text(
    provider: LLMProvider,
    provider_config: ProviderConfig,
    prompt: str,
    override: ProviderOverride | None,
):
    request = ProviderRequest(
        prompt=prompt,
        system_prompt=None,
        temperature=_resolve_param("temperature", override, default=0.1),
        max_output_tokens=_resolve_param("max_output_tokens", override),
        top_p=_resolve_param("top_p", override),
        reasoning_effort=_resolve_param("reasoning_effort", override),
        verbosity=_resolve_param("verbosity", override),
        thinking_budget=_resolve_param("thinking_budget", override),
        include_thoughts=_resolve_param("include_thoughts", override),
        metadata={"stage": BookStage.FACT_MAPPING.value, "agent": "critic"},
    )
    return await generate_with_cache(provider_config, provider, request, BookStage.FACT_MAPPING.value)


def _parse_mapping(payload: str) -> FactMappingBatch:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise ProviderResponseError("Fact mapping response was not valid JSON") from exc
    return FactMappingBatch.model_validate(data)


def _build_coverage(
    structure: BookStructure, mapping: FactMappingBatch
) -> list[SubchapterFactCoverage]:
    counts: dict[str, int] = {}
    for fact in mapping.facts:
        key = str(fact.subchapter_id)
        counts[key] = counts.get(key, 0) + 1

    coverage: list[SubchapterFactCoverage] = []
    for chapter in structure.chapters:
        for subchapter in chapter.subchapters:
            key = str(subchapter.id)
            coverage.append(
                SubchapterFactCoverage(
                    subchapter_id=subchapter.id,
                    fact_count=counts.get(key, 0),
                )
            )
    return coverage


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
