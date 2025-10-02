"""Coordinates the seven-stage writing workflow across agents."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from book_creator_providers import LLMProvider, ProviderConfig, ProviderFactory, ProviderRequest
from book_creator_providers.exceptions import ProviderResponseError
from book_creator_schemas import AgentRole, BookStage, CritiqueSeverity
from book_creator_schemas.models.book import (
    DraftFeedbackItem,
    DraftIteration,
    SubchapterDraftState,
    WritingBatch,
)

from ..cache import generate_with_cache
from ..models import ProviderOverride
from ..providers import resolve_provider_config
from .prompts import (
    WRITING_CRITIC_PROMPT,
    WRITING_IMPLEMENT_PROMPT,
    WRITING_INITIAL_PROMPT,
    WRITING_SYSTEM_PROMPT,
)


class WriterDraftEntry(BaseModel):
    """Initial writer output per subchapter."""

    subchapter_id: UUID
    content: str
    summary: str | None = None
    word_count: int | None = Field(None, ge=0)


class WriterDraftBatch(BaseModel):
    """Collection of writer drafts."""

    subchapters: list[WriterDraftEntry]
    overview: str | None = None


class CritiqueFeedback(BaseModel):
    """Feedback item emitted by critic agents."""

    message: str
    severity: CritiqueSeverity
    category: str | None = None
    rationale: str | None = None


class CritiqueEntry(BaseModel):
    """Critic analysis for a subchapter."""

    subchapter_id: UUID
    overview: str
    feedback: list[CritiqueFeedback] = Field(default_factory=list)


class CritiqueBatch(BaseModel):
    """Critic output across all subchapters."""

    subchapters: list[CritiqueEntry]
    summary: str | None = None


class ImplementationEntry(BaseModel):
    """Implementer revision output per subchapter."""

    subchapter_id: UUID
    content: str
    summary: str | None = None
    word_count: int | None = Field(None, ge=0)
    resolved_feedback: list[UUID] = Field(default_factory=list)
    notes: str | None = None


class ImplementationBatch(BaseModel):
    """Implementer output for a cycle."""

    subchapters: list[ImplementationEntry]
    summary: str | None = None


WRITER_BATCH_SCHEMA = WriterDraftBatch.model_json_schema()
CRITIQUE_BATCH_SCHEMA = CritiqueBatch.model_json_schema()
IMPLEMENT_BATCH_SCHEMA = ImplementationBatch.model_json_schema()


@dataclass
class WritingResult:
    """Final payload returned to the orchestrator."""

    batch: WritingBatch
    critique: str | None
    cost_usd: float | None


async def generate_writing_batch(
    payload: dict[str, Any],
    run_override: ProviderOverride | None,
    stage_override: ProviderOverride | None,
) -> WritingResult:
    """Execute the seven-step writing workflow for the project."""

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

    raw_project_id = payload.get("project_id")
    try:
        project_uuid = UUID(str(raw_project_id))
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        project_uuid = uuid4()

    title = payload.get("title") or "Untitled Manuscript"
    synopsis = payload.get("synopsis") or "Synopsis not available."
    guidelines = payload.get("guidelines") or []
    facts = payload.get("facts") or []
    emotional_entries = payload.get("emotional_layer") or []
    persona = payload.get("persona") or {}
    structure = payload.get("structure") or {}
    subchapter_meta = payload.get("subchapters") or []
    notes = payload.get("notes") or "None provided."
    previous_batch = payload.get("previous_batch") or {}

    cycle_count = int(payload.get("cycle_count") or 3)
    cycle_count = max(1, min(3, cycle_count))

    guidelines_json = json.dumps(guidelines, ensure_ascii=False)
    facts_json = json.dumps(facts, ensure_ascii=False)
    emotional_json = json.dumps(emotional_entries, ensure_ascii=False)
    persona_json = json.dumps(persona, ensure_ascii=False)
    structure_json = json.dumps(structure, ensure_ascii=False)
    subchapter_meta_json = json.dumps(subchapter_meta, ensure_ascii=False)
    previous_batch_json = json.dumps(previous_batch, ensure_ascii=False)

    meta_lookup: dict[str, dict[str, Any]] = {}
    for item in subchapter_meta:
        sub_id = str(item.get("id"))
        if not sub_id:
            continue
        meta_lookup[sub_id] = {
            "title": item.get("title") or "Untitled Subchapter",
            "chapter_title": item.get("chapter_title"),
            "order_label": item.get("order_label"),
            "chapter_order": item.get("chapter_order", 0),
            "sub_order": item.get("sub_order", 0),
        }

    writer_prompt = WRITING_INITIAL_PROMPT.format(
        project_id=str(project_uuid),
        title=title,
        synopsis=synopsis,
        persona_json=persona_json,
        structure_json=structure_json,
        subchapter_meta_json=subchapter_meta_json,
        guidelines_json=guidelines_json,
        facts_json=facts_json,
        emotional_json=emotional_json,
        previous_batch_json=previous_batch_json,
        notes=notes,
    )
    writer_response = await _request_writer(
        provider, provider_config, writer_prompt, effective_override
    )
    _record_cost(writer_response)
    writer_batch = _parse_writer_batch(writer_response.text)

    meta_ids = set(meta_lookup.keys())
    writer_ids = {str(entry.subchapter_id) for entry in writer_batch.subchapters}
    missing = meta_ids - writer_ids
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ProviderResponseError(
            f"Writing stage omitted drafts for subchapters: {missing_list}"
        )

    iterations_map: dict[str, list[DraftIteration]] = {sub_id: [] for sub_id in meta_lookup}
    feedback_map: dict[str, list[DraftFeedbackItem]] = {sub_id: [] for sub_id in meta_lookup}
    current_drafts: dict[str, str] = {}
    word_counts: dict[str, int | None] = {}
    last_updated: dict[str, datetime] = {}

    run_started_at = datetime.utcnow()
    summary_parts: list[str] = []
    critic_summaries: list[str] = []

    for entry in writer_batch.subchapters:
        sub_id = str(entry.subchapter_id)
        iteration = DraftIteration(
            project_id=project_uuid,
            subchapter_id=entry.subchapter_id,
            cycle=0,
            role=AgentRole.WRITER_INITIAL,
            content=entry.content.strip(),
            summary=entry.summary,
            word_count=entry.word_count,
        )
        iterations_map[sub_id].append(iteration)
        current_drafts[sub_id] = entry.content
        word_counts[sub_id] = entry.word_count
        last_updated[sub_id] = iteration.created_at

    if writer_batch.overview:
        summary_parts.append(writer_batch.overview.strip())

    critic_roles = [
        (AgentRole.WRITING_CRITIC_I, "W2: Critical Reviewer I"),
        (AgentRole.WRITING_CRITIC_II, "W4: Critical Reviewer II"),
        (AgentRole.WRITING_CRITIC_III, "W6: Critical Reviewer III"),
    ]
    implement_roles = [
        (AgentRole.WRITING_IMPLEMENTATION_I, "W3: Implementation I"),
        (AgentRole.WRITING_IMPLEMENTATION_II, "W5: Implementation II"),
        (AgentRole.WRITING_IMPLEMENTATION_III, "W7: Implementation III"),
    ]

    for cycle_index in range(cycle_count):
        critic_role, critic_label = critic_roles[cycle_index]
        implement_role, implement_label = implement_roles[cycle_index]

        drafts_payload = []
        for sub_id, meta in meta_lookup.items():
            drafts_payload.append(
                {
                    "subchapter_id": sub_id,
                    "title": meta["title"],
                    "chapter_title": meta.get("chapter_title"),
                    "order_label": meta.get("order_label"),
                    "current_draft": current_drafts.get(sub_id, ""),
                    "word_count": word_counts.get(sub_id),
                    "open_feedback": [
                        item.model_dump(mode="json")
                        for item in feedback_map[sub_id]
                        if not item.addressed
                    ],
                }
            )

        outstanding_payload = {
            "subchapters": [
                {
                    "subchapter_id": sub_id,
                    "title": meta_lookup[sub_id]["title"],
                    "feedback": [
                        item.model_dump(mode="json")
                        for item in feedback_map[sub_id]
                        if not item.addressed
                    ],
                }
                for sub_id in meta_lookup
            ]
        }

        critic_prompt = WRITING_CRITIC_PROMPT.format(
            critic_label=critic_label,
            cycle_label=cycle_index + 1,
            drafts_json=json.dumps(drafts_payload, ensure_ascii=False),
            outstanding_json=json.dumps(outstanding_payload, ensure_ascii=False),
            guidelines_json=guidelines_json,
            facts_json=facts_json,
            emotional_json=emotional_json,
            persona_json=persona_json,
            previous_batch_json=previous_batch_json,
            notes=notes,
        )
        critic_response = await _request_critic(
            provider, provider_config, critic_prompt, effective_override
        )
        _record_cost(critic_response)
        critic_batch = _parse_critic_batch(critic_response.text)

        critic_summary_parts: list[str] = []
        critic_created_at = datetime.utcnow()
        for entry in critic_batch.subchapters:
            sub_id = str(entry.subchapter_id)
            new_feedback: list[DraftFeedbackItem] = []
            for feedback in entry.feedback:
                feedback_item = DraftFeedbackItem(
                    id=uuid4(),
                    message=feedback.message.strip(),
                    severity=feedback.severity,
                    category=feedback.category,
                    rationale=feedback.rationale,
                )
                feedback_map[sub_id].append(feedback_item)
                new_feedback.append(feedback_item.model_copy(deep=True))

            critic_iteration = DraftIteration(
                project_id=project_uuid,
                subchapter_id=entry.subchapter_id,
                cycle=cycle_index,
                role=critic_role,
                content=entry.overview.strip(),
                summary=None,
                word_count=None,
                feedback=new_feedback,
            )
            iterations_map[sub_id].append(critic_iteration)
            last_updated[sub_id] = critic_iteration.created_at

        if critic_batch.summary:
            critic_summary_parts.append(critic_batch.summary.strip())
        if critic_summary_parts:
            critic_summaries.append(" ".join(critic_summary_parts))

        outstanding_for_impl = {
            "subchapters": [
                {
                    "subchapter_id": sub_id,
                    "title": meta_lookup[sub_id]["title"],
                    "feedback": [
                        item.model_dump(mode="json")
                        for item in feedback_map[sub_id]
                        if not item.addressed
                    ],
                }
                for sub_id in meta_lookup
            ]
        }

        implementation_prompt = WRITING_IMPLEMENT_PROMPT.format(
            implement_label=implement_label,
            cycle_label=cycle_index + 1,
            drafts_json=json.dumps(drafts_payload, ensure_ascii=False),
            outstanding_json=json.dumps(outstanding_for_impl, ensure_ascii=False),
            guidelines_json=guidelines_json,
            facts_json=facts_json,
            emotional_json=emotional_json,
            persona_json=persona_json,
            previous_batch_json=previous_batch_json,
            notes=notes,
        )
        implementation_response = await _request_implementer(
            provider, provider_config, implementation_prompt, effective_override
        )
        _record_cost(implementation_response)
        implementation_batch = _parse_implementation_batch(implementation_response.text)

        for entry in implementation_batch.subchapters:
            sub_id = str(entry.subchapter_id)
            resolved_ids = {str(resolved_id) for resolved_id in entry.resolved_feedback}

            iteration_summary = entry.summary.strip() if entry.summary else None
            if entry.notes:
                notes_text = entry.notes.strip()
                if iteration_summary:
                    iteration_summary = f"{iteration_summary} — Notes: {notes_text}"
                else:
                    iteration_summary = f"Notes: {notes_text}"

            current_drafts[sub_id] = entry.content
            word_counts[sub_id] = entry.word_count

            # Update feedback statuses after implementation.
            for feedback in feedback_map[sub_id]:
                if str(feedback.id) in resolved_ids:
                    feedback.addressed = True
                    # iteration ID is set below; temporarily mark with None.
                    feedback.addressed_in_iteration = None

            implementation_iteration = DraftIteration(
                project_id=project_uuid,
                subchapter_id=entry.subchapter_id,
                cycle=cycle_index,
                role=implement_role,
                content=entry.content.strip(),
                summary=iteration_summary,
                word_count=entry.word_count,
            )

            for feedback in feedback_map[sub_id]:
                if feedback.addressed and feedback.addressed_in_iteration is None:
                    feedback.addressed_in_iteration = implementation_iteration.id

            feedback_snapshot = [
                item.model_copy(deep=True) for item in feedback_map[sub_id]
            ]
            implementation_iteration = implementation_iteration.model_copy(
                update={"feedback": feedback_snapshot}
            )

            iterations_map[sub_id].append(implementation_iteration)
            last_updated[sub_id] = implementation_iteration.created_at

        if implementation_batch.summary:
            summary_parts.append(implementation_batch.summary.strip())

    sorted_meta = sorted(
        meta_lookup.items(),
        key=lambda item: (item[1].get("chapter_order", 0), item[1].get("sub_order", 0)),
    )

    subchapter_states: list[SubchapterDraftState] = []
    total_word_count = 0
    for sub_id, meta in sorted_meta:
        iterations = [iter.model_copy(deep=True) for iter in iterations_map[sub_id]]
        all_feedback = [item for item in feedback_map[sub_id]]
        outstanding_feedback = [
            item.model_copy(deep=True) for item in all_feedback if not item.addressed
        ]

        if word_counts.get(sub_id):
            total_word_count += word_counts[sub_id] or 0

        status = "ready" if not outstanding_feedback else "in_review"
        if not iterations:
            status = "draft"

        current_cycle = max((iteration.cycle for iteration in iterations), default=0)
        final_iteration_id = iterations[-1].id if iterations else None
        final_word_count = word_counts.get(sub_id)
        last_update = last_updated.get(sub_id, datetime.utcnow())

        subchapter_states.append(
            SubchapterDraftState(
                subchapter_id=UUID(sub_id),
                title=meta["title"],
                chapter_title=meta.get("chapter_title"),
                order_label=meta.get("order_label"),
                current_cycle=current_cycle,
                status=status,
                iterations=iterations,
                outstanding_feedback=outstanding_feedback,
                final_iteration_id=final_iteration_id,
                final_word_count=final_word_count,
                last_updated=last_update,
            )
        )

    readiness = "ready" if all(state.status == "ready" for state in subchapter_states) else "draft"
    total_word_count = total_word_count or None
    summary_text = "\n\n".join(part for part in summary_parts if part)
    critique_text = "\n\n".join(part for part in critic_summaries if part)

    updated_at = max(last_updated.values(), default=datetime.utcnow())

    batch = WritingBatch(
        project_id=project_uuid,
        cycle_count=cycle_count,
        readiness=readiness,
        summary=summary_text or None,
        subchapters=subchapter_states,
        total_word_count=total_word_count,
        created_at=run_started_at,
        updated_at=updated_at,
    )

    return WritingResult(
        batch=batch,
        critique=critique_text or None,
        cost_usd=total_cost if cost_samples else None,
    )


async def _request_writer(
    provider: LLMProvider,
    provider_config: ProviderConfig | None,
    prompt: str,
    override: ProviderOverride | None,
):
    config = provider_config or resolve_provider_config(override)
    request = ProviderRequest(
        prompt=prompt,
        system_prompt=WRITING_SYSTEM_PROMPT,
        json_schema=WRITER_BATCH_SCHEMA,
        temperature=_resolve_param("temperature", override, 0.7),
        max_output_tokens=_resolve_param("max_output_tokens", override),
        top_p=_resolve_param("top_p", override),
        reasoning_effort=_resolve_param("reasoning_effort", override),
        verbosity=_resolve_param("verbosity", override),
        thinking_budget=_resolve_param("thinking_budget", override),
        include_thoughts=_resolve_param("include_thoughts", override),
        metadata={"stage": BookStage.WRITING.value, "agent": "writer"},
    )
    return await generate_with_cache(config, provider, request, BookStage.WRITING.value)


async def _request_critic(
    provider: LLMProvider,
    provider_config: ProviderConfig | None,
    prompt: str,
    override: ProviderOverride | None,
):
    config = provider_config or resolve_provider_config(override)
    request = ProviderRequest(
        prompt=prompt,
        system_prompt=WRITING_SYSTEM_PROMPT,
        json_schema=CRITIQUE_BATCH_SCHEMA,
        temperature=_resolve_param("temperature", override, 0.2),
        max_output_tokens=_resolve_param("max_output_tokens", override),
        top_p=_resolve_param("top_p", override),
        reasoning_effort=_resolve_param("reasoning_effort", override),
        verbosity=_resolve_param("verbosity", override),
        thinking_budget=_resolve_param("thinking_budget", override),
        include_thoughts=_resolve_param("include_thoughts", override),
        metadata={"stage": BookStage.WRITING.value, "agent": "critic"},
    )
    return await generate_with_cache(config, provider, request, BookStage.WRITING.value)


async def _request_implementer(
    provider: LLMProvider,
    provider_config: ProviderConfig | None,
    prompt: str,
    override: ProviderOverride | None,
):
    config = provider_config or resolve_provider_config(override)
    request = ProviderRequest(
        prompt=prompt,
        system_prompt=WRITING_SYSTEM_PROMPT,
        json_schema=IMPLEMENT_BATCH_SCHEMA,
        temperature=_resolve_param("temperature", override, 0.5),
        max_output_tokens=_resolve_param("max_output_tokens", override),
        top_p=_resolve_param("top_p", override),
        reasoning_effort=_resolve_param("reasoning_effort", override),
        verbosity=_resolve_param("verbosity", override),
        thinking_budget=_resolve_param("thinking_budget", override),
        include_thoughts=_resolve_param("include_thoughts", override),
        metadata={"stage": BookStage.WRITING.value, "agent": "implementer"},
    )
    return await generate_with_cache(config, provider, request, BookStage.WRITING.value)


def _parse_writer_batch(payload: str) -> WriterDraftBatch:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise ProviderResponseError("Writer response was not valid JSON") from exc
    return WriterDraftBatch.model_validate(data)


def _parse_critic_batch(payload: str) -> CritiqueBatch:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise ProviderResponseError("Critic response was not valid JSON") from exc
    return CritiqueBatch.model_validate(data)


def _parse_implementation_batch(payload: str) -> ImplementationBatch:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise ProviderResponseError("Implementation response was not valid JSON") from exc
    return ImplementationBatch.model_validate(data)


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
