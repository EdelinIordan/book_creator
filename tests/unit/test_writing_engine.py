"""Quality assurance tests for the writing orchestrator engine."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from book_creator_providers.base import ProviderResponse
from book_creator_schemas import AgentRole, CritiqueSeverity

from services.orchestrator.app.writing.engine import (
    CritiqueBatch,
    CritiqueEntry,
    CritiqueFeedback,
    ImplementationBatch,
    ImplementationEntry,
    WriterDraftBatch,
    WriterDraftEntry,
    generate_writing_batch,
)
from tests.utils.prompts import extract_json_block


pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_writing_engine_marks_feedback_resolved(monkeypatch):
    """End-to-end check that the writing engine resolves critic feedback cues."""

    project_id = uuid4()
    subchapter_id = uuid4()

    async def fake_writer(provider, provider_config, prompt, override):
        batch = WriterDraftBatch(
            subchapters=[
                WriterDraftEntry(
                    subchapter_id=subchapter_id,
                    content="Initial draft that needs a stronger hook.",
                    summary="Covers baseline facts",
                    word_count=240,
                )
            ],
            overview="Drafts prepared for review.",
        )
        return ProviderResponse(
            text=batch.model_dump_json(),
            raw={"cached": False},
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
            latency_ms=0.0,
        )

    async def fake_critic(provider, provider_config, prompt, override):
        batch = CritiqueBatch(
            subchapters=[
                CritiqueEntry(
                    subchapter_id=subchapter_id,
                    overview="Lead paragraph lacks a clear anecdote.",
                    feedback=[
                        CritiqueFeedback(
                            message="Open with the emotional hook from the persona notes.",
                            severity=CritiqueSeverity.WARNING,
                            category="structure",
                            rationale="Readers need an immediate narrative anchor.",
                        )
                    ],
                )
            ],
            summary="Tighten openings across the chapter.",
        )
        return ProviderResponse(
            text=batch.model_dump_json(),
            raw={"cached": False},
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
            latency_ms=0.0,
        )

    async def fake_implementer(provider, provider_config, prompt, override):
        outstanding = extract_json_block(prompt, "Open feedback items with IDs (JSON)")
        resolved_ids: list[UUID] = []
        for entry in outstanding.get("subchapters", []):
            for item in entry.get("feedback", []):
                resolved_ids.append(UUID(item["id"]))

        batch = ImplementationBatch(
            subchapters=[
                ImplementationEntry(
                    subchapter_id=subchapter_id,
                    content="Reworked draft featuring the persona's childhood story as the hook.",
                    summary="Introduced emotional hook per feedback.",
                    word_count=315,
                    resolved_feedback=resolved_ids,
                    notes="Hook integrated and transitions smoothed.",
                )
            ],
            summary="Implemented critic recommendations across drafts.",
        )
        return ProviderResponse(
            text=batch.model_dump_json(),
            raw={"cached": False},
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
            latency_ms=0.0,
        )

    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(
        "services.orchestrator.app.writing.engine.ProviderFactory.create",
        lambda config: object(),
    )
    monkeypatch.setattr(
        "services.orchestrator.app.writing.engine._request_writer",
        fake_writer,
    )
    monkeypatch.setattr(
        "services.orchestrator.app.writing.engine._request_critic",
        fake_critic,
    )
    monkeypatch.setattr(
        "services.orchestrator.app.writing.engine._request_implementer",
        fake_implementer,
    )

    payload = {
        "project_id": str(project_id),
        "title": "Echoes of Empires",
        "synopsis": "Comparative history of bureaucratic legacies.",
        "structure": {"chapters": []},
        "guidelines": [
            {
                "subchapter_id": str(subchapter_id),
                "objectives": ["Showcase relatable opening vignette"],
                "must_include_facts": [],
            }
        ],
        "facts": [],
        "emotional_layer": [
            {
                "subchapter_id": str(subchapter_id),
                "story_hook": "Describe the protagonist's first day managing the archives.",
            }
        ],
        "subchapters": [
            {
                "id": str(subchapter_id),
                "title": "Origins of Administrative Rigor",
                "chapter_title": "Foundations",
                "order_label": "1.1",
                "chapter_order": 1,
                "sub_order": 1,
            }
        ],
        "cycle_count": 1,
        "notes": "Focus on narrative energy in intros.",
    }

    result = await generate_writing_batch(payload, run_override=None, stage_override=None)

    assert result.critique is not None and "openings" in result.critique.lower()

    batch = result.batch
    assert batch.readiness == "ready"
    assert batch.total_word_count == 315

    assert len(batch.subchapters) == 1
    draft_state = batch.subchapters[0]
    assert draft_state.status == "ready"
    assert draft_state.outstanding_feedback == []
    assert draft_state.final_word_count == 315

    role_sequence = [iteration.role for iteration in draft_state.iterations]
    assert role_sequence[0] == AgentRole.WRITER_INITIAL
    assert AgentRole.WRITING_IMPLEMENTATION_I in role_sequence

    implementation_iteration = next(
        iteration
        for iteration in draft_state.iterations
        if iteration.role == AgentRole.WRITING_IMPLEMENTATION_I
    )
    assert all(item.addressed for item in implementation_iteration.feedback)


async def test_writing_engine_keeps_outstanding_feedback(monkeypatch):
    """If implementers omit feedback IDs, readiness should remain in draft state."""

    project_id = uuid4()
    subchapter_id = uuid4()

    async def fake_writer(provider, provider_config, prompt, override):
        batch = WriterDraftBatch(
            subchapters=[
                WriterDraftEntry(
                    subchapter_id=subchapter_id,
                    content="First draft missing the anecdote.",
                    summary=None,
                    word_count=200,
                )
            ],
            overview="Initial drafts ready.",
        )
        return ProviderResponse(
            text=batch.model_dump_json(),
            raw={"cached": False},
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
            latency_ms=0.0,
        )

    async def fake_critic(provider, provider_config, prompt, override):
        batch = CritiqueBatch(
            subchapters=[
                CritiqueEntry(
                    subchapter_id=subchapter_id,
                    overview="Add the persona's hook to the intro.",
                    feedback=[
                        CritiqueFeedback(
                            message="Introduce the persona hook in the first paragraph.",
                            severity=CritiqueSeverity.ERROR,
                            category="tone",
                            rationale="Launches narrative with emotional clarity.",
                        )
                    ],
                )
            ],
            summary="Implementer still needs to address critical feedback.",
        )
        return ProviderResponse(
            text=batch.model_dump_json(),
            raw={"cached": False},
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
            latency_ms=0.0,
        )

    async def fake_implementer(provider, provider_config, prompt, override):
        batch = ImplementationBatch(
            subchapters=[
                ImplementationEntry(
                    subchapter_id=subchapter_id,
                    content="Draft revised but hook still pending.",
                    summary="Partial edits applied.",
                    word_count=210,
                    resolved_feedback=[],
                )
            ],
            summary="Implementer delivered revisions but missed key feedback.",
        )
        return ProviderResponse(
            text=batch.model_dump_json(),
            raw={"cached": False},
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
            latency_ms=0.0,
        )

    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(
        "services.orchestrator.app.writing.engine.ProviderFactory.create",
        lambda config: object(),
    )
    monkeypatch.setattr(
        "services.orchestrator.app.writing.engine._request_writer",
        fake_writer,
    )
    monkeypatch.setattr(
        "services.orchestrator.app.writing.engine._request_critic",
        fake_critic,
    )
    monkeypatch.setattr(
        "services.orchestrator.app.writing.engine._request_implementer",
        fake_implementer,
    )

    payload = {
        "project_id": str(project_id),
        "title": "Echoes of Empires",
        "synopsis": "Comparative history of bureaucratic legacies.",
        "structure": {"chapters": []},
        "guidelines": [],
        "facts": [],
        "emotional_layer": [],
        "subchapters": [
            {
                "id": str(subchapter_id),
                "title": "Origins of Administrative Rigor",
                "chapter_title": "Foundations",
                "order_label": "1.1",
                "chapter_order": 1,
                "sub_order": 1,
            }
        ],
        "cycle_count": 1,
    }

    result = await generate_writing_batch(payload, run_override=None, stage_override=None)
    batch = result.batch

    assert batch.readiness == "draft"
    draft_state = batch.subchapters[0]
    assert draft_state.status == "in_review"
    assert len(draft_state.outstanding_feedback) == 1
    assert draft_state.outstanding_feedback[0].addressed is False
