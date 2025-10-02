"""Orchestrates the creative director guideline workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from book_creator_providers import LLMProvider, ProviderFactory, ProviderRequest
from book_creator_providers.exceptions import ProviderResponseError
from book_creator_schemas import AgentRole, BookStage
from book_creator_schemas.models.book import CreativeGuideline, CreativeGuidelineBatch

from ..models import ProviderOverride
from ..providers import resolve_provider_config
from .prompts import (
    GUIDELINES_CRITIQUE_PROMPT,
    GUIDELINES_FINAL_PROMPT,
    GUIDELINES_PROPOSAL_PROMPT,
    GUIDELINES_SYSTEM_PROMPT,
)

GUIDELINE_BATCH_SCHEMA = CreativeGuidelineBatch.model_json_schema()


@dataclass
class CreativeGuidelineResult:
    """Return payload for the creative director stage."""

    batch: CreativeGuidelineBatch
    critique: str | None
    cost_usd: float | None


async def generate_creative_guidelines(
    payload: dict[str, Any],
    run_override: ProviderOverride | None,
    stage_override: ProviderOverride | None,
) -> CreativeGuidelineResult:
    """Execute the assistant → critic → final creative director sequence."""

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

    project_id = payload.get("project_id", "")
    title = payload.get("title") or "Untitled Manuscript"
    synopsis = payload.get("synopsis") or "Synopsis not available."
    preferences = payload.get("preferences") or "No additional preferences provided."
    persona_json = json.dumps(payload.get("persona") or {}, ensure_ascii=False)
    structure_json = json.dumps(payload.get("structure") or {}, ensure_ascii=False)
    facts_json = json.dumps(payload.get("facts") or [], ensure_ascii=False)
    emotional_json = json.dumps(payload.get("emotional_layer") or [], ensure_ascii=False)
    target_version = int(payload.get("target_version") or 1)

    proposal_response = await _request_batch(
        provider,
        GUIDELINES_PROPOSAL_PROMPT.format(
            project_id=project_id,
            title=title,
            synopsis=synopsis,
            persona_json=persona_json,
            preferences=preferences,
            structure_json=structure_json,
            facts_json=facts_json,
            emotional_json=emotional_json,
        ),
        effective_override,
    )
    _record_cost(proposal_response)
    proposal = _parse_batch(proposal_response.text)

    proposal_json = json.dumps(proposal.model_dump(mode="json"), ensure_ascii=False)

    critique_response = await _request_text(
        provider,
        GUIDELINES_CRITIQUE_PROMPT.format(batch_json=proposal_json),
        effective_override,
    )
    _record_cost(critique_response)
    critique_text = critique_response.text.strip()

    final_response = await _request_batch(
        provider,
        GUIDELINES_FINAL_PROMPT.format(
            project_id=project_id,
            title=title,
            synopsis=synopsis,
            persona_json=persona_json,
            preferences=preferences,
            structure_json=structure_json,
            facts_json=facts_json,
            emotional_json=emotional_json,
            critique_text=critique_text or "No critique provided.",
            batch_json=proposal_json,
            target_version=target_version,
        ),
        effective_override,
    )
    _record_cost(final_response)
    final_batch = _parse_batch(final_response.text)

    normalised_batch = _ensure_final_metadata(final_batch, project_id, target_version)

    return CreativeGuidelineResult(
        batch=normalised_batch,
        critique=critique_text or None,
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
        system_prompt=GUIDELINES_SYSTEM_PROMPT,
        json_schema=GUIDELINE_BATCH_SCHEMA,
        temperature=_resolve_param("temperature", override, 0.4),
        max_output_tokens=_resolve_param("max_output_tokens", override),
        top_p=_resolve_param("top_p", override),
        reasoning_effort=_resolve_param("reasoning_effort", override),
        verbosity=_resolve_param("verbosity", override),
        thinking_budget=_resolve_param("thinking_budget", override),
        include_thoughts=_resolve_param("include_thoughts", override),
        metadata={"stage": BookStage.GUIDELINES.value},
    )
    response = await generate_with_cache(
        provider_config, provider, request, BookStage.GUIDELINES.value
    )
    return _parse_batch(response.text)


async def _request_text(
    provider: LLMProvider,
    provider_config: ProviderConfig,
    prompt: str,
    override: ProviderOverride | None,
):
    request = ProviderRequest(
        prompt=prompt,
        system_prompt=None,
        temperature=_resolve_param("temperature", override, 0.2),
        max_output_tokens=_resolve_param("max_output_tokens", override),
        top_p=_resolve_param("top_p", override),
        reasoning_effort=_resolve_param("reasoning_effort", override),
        verbosity=_resolve_param("verbosity", override),
        thinking_budget=_resolve_param("thinking_budget", override),
        include_thoughts=_resolve_param("include_thoughts", override),
        metadata={"stage": BookStage.GUIDELINES.value, "agent": "critic"},
    )
    return await generate_with_cache(provider_config, provider, request, BookStage.GUIDELINES.value)


def _parse_batch(payload: str) -> CreativeGuidelineBatch:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise ProviderResponseError("Creative guideline response was not valid JSON") from exc
    return CreativeGuidelineBatch.model_validate(data)


def _ensure_final_metadata(
    batch: CreativeGuidelineBatch, project_id: str, target_version: int
) -> CreativeGuidelineBatch:
    final_guidelines: list[CreativeGuideline] = []
    for guideline in batch.guidelines:
        final_guidelines.append(
            guideline.model_copy(
                update={
                    "project_id": project_id or guideline.project_id,
                    "version": target_version,
                    "status": "final",
                    "created_by": AgentRole.CREATIVE_DIRECTOR_FINAL,
                    "updated_at": guideline.updated_at,
                }
            )
        )

    return batch.model_copy(
        update={
            "project_id": project_id or batch.project_id,
            "version": target_version,
            "guidelines": final_guidelines,
            "readiness": "ready",
        }
    )


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
