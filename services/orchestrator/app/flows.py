"""Prefect flows coordinating the book creation stages."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from time import perf_counter
from uuid import uuid4

from prefect import flow

from book_creator_observability import (
    log_context,
    observe_provider_response,
    observe_stage_duration,
)
from book_creator_providers import ProviderFactory, ProviderRequest
from book_creator_schemas import BookStage

from .cache import generate_with_cache
from .emotional import generate_emotional_layer
from .fact_mapping import generate_fact_mapping
from .guidelines import generate_creative_guidelines
from .models import ProviderOverride, RunRequest, RunResponse, StageRunResult
from .providers import resolve_provider_config
from .research.engine import generate_research_prompts
from .structure.engine import generate_structure
from .title.engine import generate_titles
from .writing import generate_writing_batch


logger = logging.getLogger(__name__)
SERVICE_NAME = "orchestrator"


@flow(name="book-creator-flow", version="0.1.0")
async def run_book_flow(payload: RunRequest) -> RunResponse:
    run_id = uuid4()
    stage_results: list[StageRunResult] = []
    provider_name: str = (
        payload.provider.name if payload.provider and payload.provider.name else "unknown"
    )
    if payload.provider:
        try:
            provider_name = resolve_provider_config(payload.provider).name
        except Exception:  # pragma: no cover - falls back when env config missing
            provider_name = provider_name
    base_context: dict[str, str] = {"run_id": str(run_id)}
    if payload.project_id:
        base_context["project_id"] = str(payload.project_id)

    with log_context(**base_context):
        logger.info(
            "Starting orchestrator run",
            extra={"stage_count": len(payload.stages)},
        )

        for stage_req in payload.stages:
            stage_name = stage_req.stage.value
            stage_override = stage_req.provider_override
            effective_override = _merge_overrides(stage_override, payload.provider)
            provider_config = resolve_provider_config(effective_override)
            provider_name = provider_config.name

            stage_start = perf_counter()
            outcome = "success"

            with log_context(stage=stage_name, provider=provider_config.name):
                logger.info(
                    "Executing stage",
                    extra={"prompt_length": len(stage_req.prompt)},
                )

                try:
                    if stage_req.stage == BookStage.STRUCTURE:
                        result = await generate_structure(
                            idea_text=stage_req.prompt,
                            context="",
                            run_override=payload.provider,
                            stage_override=stage_override,
                        )
                        stage_results.append(
                            StageRunResult(
                                stage=stage_req.stage,
                                output=result.summary_text,
                                model=provider_config.name,
                                prompt_tokens=0,
                                completion_tokens=0,
                                latency_ms=None,
                                cost_usd=getattr(result, "cost_usd", None),
                                received_at=result.structure.updated_at,
                                structured_output=result.structure.model_dump(mode="json"),
                                extras={"critiques": result.critiques},
                            )
                        )
                        logger.info(
                            "Structure stage completed",
                            extra={"critique_count": len(result.critiques)},
                        )
                        continue

                    if stage_req.stage == BookStage.TITLE:
                        title_result = await generate_titles(
                            synopsis=stage_req.prompt,
                            chapters_summary="See structure lab for chapters",
                            audience="General nonfiction readers",
                            run_override=payload.provider,
                            stage_override=stage_override,
                        )
                        stage_results.append(
                            StageRunResult(
                                stage=stage_req.stage,
                                output="; ".join([t.title for t in title_result.batch.options]),
                                model=provider_config.name,
                                prompt_tokens=0,
                                completion_tokens=0,
                                latency_ms=None,
                                cost_usd=getattr(title_result, "cost_usd", None),
                                received_at=datetime.utcnow(),
                                structured_output=title_result.batch.model_dump(mode="json"),
                                extras={"critique": title_result.critique},
                            )
                        )
                        logger.info(
                            "Title stage completed",
                            extra={"option_count": len(title_result.batch.options)},
                        )
                        continue

                    if stage_req.stage == BookStage.RESEARCH:
                        try:
                            payload_data = json.loads(stage_req.prompt)
                        except json.JSONDecodeError:
                            payload_data = {
                                "synopsis": stage_req.prompt,
                                "structure_summary": "",
                                "guidelines": "",
                            }
                        research_result = await generate_research_prompts(
                            synopsis=payload_data.get("synopsis", ""),
                            structure_summary=payload_data.get("structure_summary", ""),
                            guidelines=payload_data.get("guidelines", ""),
                            run_override=payload.provider,
                            stage_override=stage_override,
                        )
                        stage_results.append(
                            StageRunResult(
                                stage=stage_req.stage,
                                output="\n\n".join(
                                    [prompt.prompt_text for prompt in research_result.batch.prompts]
                                ),
                                model=provider_config.name,
                                prompt_tokens=0,
                                completion_tokens=0,
                                latency_ms=None,
                                cost_usd=getattr(research_result, "cost_usd", None),
                                received_at=datetime.utcnow(),
                                structured_output=research_result.batch.model_dump(mode="json"),
                                extras={"critique": research_result.critique},
                            )
                        )
                        logger.info(
                            "Research stage completed",
                            extra={"prompt_count": len(research_result.batch.prompts)},
                        )
                        continue

                    if stage_req.stage == BookStage.FACT_MAPPING:
                        try:
                            mapping_payload = json.loads(stage_req.prompt)
                        except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
                            raise ValueError("Fact mapping stage requires JSON payload") from exc

                        fact_mapping = await generate_fact_mapping(
                            payload=mapping_payload,
                            run_override=payload.provider,
                            stage_override=stage_override,
                        )
                        coverage_payload = [
                            item.model_dump(mode="json") for item in fact_mapping.batch.coverage
                        ]
                        stage_results.append(
                            StageRunResult(
                                stage=stage_req.stage,
                                output=f"Mapped {len(fact_mapping.batch.facts)} facts",
                                model=provider_config.name,
                                prompt_tokens=0,
                                completion_tokens=0,
                                latency_ms=None,
                                cost_usd=getattr(fact_mapping, "cost_usd", None),
                                received_at=fact_mapping.batch.created_at,
                                structured_output=fact_mapping.batch.model_dump(mode="json"),
                                extras={
                                    "critique": fact_mapping.critique,
                                    "coverage": coverage_payload,
                                    "fact_count": len(fact_mapping.batch.facts),
                                },
                            )
                        )
                        logger.info(
                            "Fact mapping stage completed",
                            extra={"fact_count": len(fact_mapping.batch.facts)},
                        )
                        continue

                    if stage_req.stage == BookStage.EMOTIONAL:
                        try:
                            emotional_payload = json.loads(stage_req.prompt)
                        except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
                            raise ValueError("Emotional stage requires JSON payload") from exc

                        emotional_result = await generate_emotional_layer(
                            payload=emotional_payload,
                            run_override=payload.provider,
                            stage_override=stage_override,
                        )
                        entries_count = len(emotional_result.batch.entries)
                        stage_results.append(
                            StageRunResult(
                                stage=stage_req.stage,
                                output=f"Persona crafted with {entries_count} emotional entries",
                                model=provider_config.name,
                                prompt_tokens=0,
                                completion_tokens=0,
                                latency_ms=None,
                                cost_usd=getattr(emotional_result, "cost_usd", None),
                                received_at=emotional_result.batch.created_at,
                                structured_output=emotional_result.batch.model_dump(mode="json"),
                                extras={"critique": emotional_result.critique},
                            )
                        )
                        logger.info(
                            "Emotional stage completed",
                            extra={"entry_count": entries_count},
                        )
                        continue

                    if stage_req.stage == BookStage.GUIDELINES:
                        try:
                            guideline_payload = json.loads(stage_req.prompt)
                        except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
                            raise ValueError("Guidelines stage requires JSON payload") from exc

                        guideline_result = await generate_creative_guidelines(
                            payload=guideline_payload,
                            run_override=payload.provider,
                            stage_override=stage_override,
                        )
                        packet_count = len(guideline_result.batch.guidelines)
                        stage_results.append(
                            StageRunResult(
                                stage=stage_req.stage,
                                output=f"Guidelines prepared for {packet_count} subchapters",
                                model=provider_config.name,
                                prompt_tokens=0,
                                completion_tokens=0,
                                latency_ms=None,
                                cost_usd=getattr(guideline_result, "cost_usd", None),
                                received_at=guideline_result.batch.created_at,
                                structured_output=guideline_result.batch.model_dump(mode="json"),
                                extras={"critique": guideline_result.critique},
                            )
                        )
                        logger.info(
                            "Guidelines stage completed",
                            extra={"guideline_count": packet_count},
                        )
                        continue

                    if stage_req.stage == BookStage.WRITING:
                        try:
                            writing_payload = json.loads(stage_req.prompt)
                        except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
                            raise ValueError("Writing stage requires JSON payload") from exc

                        writing_result = await generate_writing_batch(
                            payload=writing_payload,
                            run_override=payload.provider,
                            stage_override=stage_override,
                        )
                        subchapter_count = len(writing_result.batch.subchapters)
                        stage_results.append(
                            StageRunResult(
                                stage=stage_req.stage,
                                output=f"Writing cycles completed for {subchapter_count} subchapters",
                                model=provider_config.name,
                                prompt_tokens=0,
                                completion_tokens=0,
                                latency_ms=None,
                                cost_usd=getattr(writing_result, "cost_usd", None),
                                received_at=writing_result.batch.updated_at,
                                structured_output=writing_result.batch.model_dump(mode="json"),
                                extras={"critique": writing_result.critique},
                            )
                        )
                        logger.info(
                            "Writing stage completed",
                            extra={"subchapter_count": subchapter_count},
                        )
                        continue

                    provider = ProviderFactory.create(provider_config)
                    request = ProviderRequest(
                        prompt=stage_req.prompt,
                        system_prompt=None,
                        temperature=_resolve_param(
                            "temperature",
                            effective_override,
                            provider_config.settings.temperature,
                        ),
                        max_output_tokens=_resolve_param(
                            "max_output_tokens",
                            effective_override,
                            provider_config.settings.max_output_tokens,
                        ),
                        top_p=_resolve_param(
                            "top_p", effective_override, provider_config.settings.top_p
                        ),
                        reasoning_effort=_resolve_param(
                            "reasoning_effort",
                            effective_override,
                            provider_config.settings.reasoning_effort,
                        ),
                        verbosity=_resolve_param(
                            "verbosity",
                            effective_override,
                            provider_config.settings.verbosity,
                        ),
                        thinking_budget=_resolve_param(
                            "thinking_budget",
                            effective_override,
                            provider_config.settings.thinking_budget,
                        ),
                        include_thoughts=_resolve_param(
                            "include_thoughts",
                            effective_override,
                            provider_config.settings.include_thoughts,
                        ),
                        metadata={"stage": stage_req.stage.value},
                    )
                    response = await generate_with_cache(
                        provider_config, provider, request, stage_name
                    )
                    observe_provider_response(
                        stage=stage_name,
                        provider=provider_config.name,
                        service_name=SERVICE_NAME,
                        response=response,
                    )
                    stage_results.append(
                        StageRunResult(
                            stage=stage_req.stage,
                            output=response.text,
                            model=response.model,
                            prompt_tokens=response.prompt_tokens,
                            completion_tokens=response.completion_tokens,
                            latency_ms=response.latency_ms,
                            cost_usd=response.cost_usd,
                            received_at=response.received_at,
                        )
                    )
                    logger.info(
                        "Stage completed via provider",
                        extra={
                            "prompt_tokens": response.prompt_tokens,
                            "completion_tokens": response.completion_tokens,
                            "latency_ms": response.latency_ms or 0,
                            "output_chars": len(response.text or ""),
                        },
                    )
                except Exception:
                    outcome = "error"
                    logger.exception("Stage execution failed")
                    raise
                finally:
                    observe_stage_duration(
                        stage=stage_name,
                        duration_seconds=perf_counter() - stage_start,
                        service_name=SERVICE_NAME,
                        status=outcome,
                    )

        logger.info(
            "Orchestrator run finished",
            extra={"stage_count": len(stage_results)},
        )

    return RunResponse(
        run_id=run_id,
        provider_name=provider_name,
        stages=stage_results,
    )


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


def _resolve_param(attr: str, override: ProviderOverride | None, default) -> int | float | None:
    if override is not None:
        value = getattr(override, attr, None)
        if value is not None:
            return value
    return default
