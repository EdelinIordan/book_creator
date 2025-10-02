"""Tests for the Prefect flow using the mock provider."""

import json
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from book_creator_schemas import BookStage
from book_creator_providers.base import (
    LLMProvider,
    ProviderCapabilities,
    ProviderRequest,
    ProviderResponse,
)

from services.orchestrator.app.flows import run_book_flow
from services.orchestrator.app.models import ProviderOverride, RunRequest, StageRunRequest
from services.orchestrator.app.writing.engine import SubchapterDraftState, WritingBatch


pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _StubStructureProvider(LLMProvider):
    name = "mock"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_json_mode=True)

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        if request.json_schema and "facts" in request.json_schema.get("properties", {}):
            payload = {
                "project_id": str(uuid4()),
                "facts": [
                    {
                        "id": str(uuid4()),
                        "project_id": str(uuid4()),
                        "subchapter_id": str(uuid4()),
                        "upload_id": 1,
                        "prompt_index": 0,
                        "summary": "Mapped fact",
                        "detail": "Mapped fact detail",
                        "citation": {
                            "source_title": "Doc",
                            "source_type": "other",
                        },
                    }
                ],
                "coverage": [
                    {
                        "subchapter_id": str(uuid4()),
                        "fact_count": 1,
                    }
                ],
            }
            return ProviderResponse(
                text=json.dumps(payload),
                raw={},
                model="stub-model",
                prompt_tokens=12,
                completion_tokens=20,
            )
        if request.json_schema and "chapters" in request.json_schema.get("properties", {}):
            payload = {
                "project_id": str(uuid4()),
                "version": 1,
                "chapters": [
                    {
                        "id": str(uuid4()),
                        "title": "Chapter 1",
                        "summary": "Summary",
                        "order": 1,
                        "subchapters": [
                            {
                                "id": str(uuid4()),
                                "title": "Section 1",
                                "summary": "Details",
                                "order": 1,
                                "learning_objectives": [],
                                "related_subchapters": [],
                            }
                        ],
                    }
                ],
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "synopsis": "Stub synopsis",
            }
            return ProviderResponse(
                text=json.dumps(payload),
                raw={},
                model="stub-model",
                prompt_tokens=10,
                completion_tokens=50,
            )
        if request.json_schema and "options" in request.json_schema.get("properties", {}):
            payload = {
                "options": [
                    {"title": "Blueprints of Empire", "rationale": "Highlights theme."},
                    {"title": "Power by Ledger", "rationale": "Focuses on records."},
                    {"title": "Governance Without Borders", "rationale": "Global scope."},
                    {"title": "Empires Engineered", "rationale": "Innovation angle."},
                    {"title": "Administrative DNA", "rationale": "Metaphor for governance."},
                ]
            }
            return ProviderResponse(
                text=json.dumps(payload),
                raw={},
                model="stub-model",
                prompt_tokens=8,
                completion_tokens=30,
            )
        if request.json_schema and "prompts" in request.json_schema.get("properties", {}):
            payload = {
                "prompts": [
                    {
                        "focus_summary": "Logistics innovations in early empires",
                        "focus_subchapters": ["1.1", "1.2"],
                        "prompt_text": "Investigate logistical reforms with primary sources.",
                        "desired_sources": ["academic_journal", "government_report"],
                        "additional_notes": "Prioritise quantitative data where possible.",
                    },
                    {
                        "focus_summary": "Cultural narratives sustaining bureaucracy",
                        "focus_subchapters": ["2.1"],
                        "prompt_text": "Collect case studies showing stories that supported administrative trust.",
                        "desired_sources": ["book", "expert_interview"],
                        "additional_notes": None,
                    },
                    {
                        "focus_summary": "Modern parallels of meritocratic exams",
                        "focus_subchapters": ["2.2"],
                        "prompt_text": "Compare imperial exam systems with modern civil service testing.",
                        "desired_sources": ["academic_journal", "news_article"],
                        "additional_notes": "Highlight measurable outcomes.",
                    },
                ]
            }
            return ProviderResponse(
                text=json.dumps(payload),
                raw={},
                model="stub-model",
                prompt_tokens=12,
                completion_tokens=35,
            )
        elif (
            "Provide a concise critique" in request.prompt
            or "Evaluate diversity" in request.prompt
            or "Review the following research tasks" in request.prompt
        ):
            text = "Critique: expand middle chapters"
            return ProviderResponse(
                text=text,
                raw={},
                model="stub-model",
                prompt_tokens=5,
                completion_tokens=10,
            )
        else:
            return ProviderResponse(
                text="Summary text",
                raw={},
                model="stub-model",
                prompt_tokens=5,
                completion_tokens=10,
            )


async def test_run_book_flow_with_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(
        "services.orchestrator.app.flows.ProviderFactory.create",
        lambda config: _StubStructureProvider(),
    )
    payload = RunRequest(
        project_id=uuid4(),
        provider=ProviderOverride(name="mock"),
        stages=[
            StageRunRequest(stage=BookStage.IDEA, prompt="Give me an idea summary."),
        ],
    )
    response = await run_book_flow(payload)
    assert response.provider_name == "mock"
    assert len(response.stages) == 1
    assert "Summary" in response.stages[0].output
    assert response.stages[0].extras is None


async def test_stage_specific_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(
        "services.orchestrator.app.flows.ProviderFactory.create",
        lambda config: _StubStructureProvider(),
    )
    stage_override = ProviderOverride(name="mock", temperature=0.2)
    payload = RunRequest(
        project_id=uuid4(),
        provider=ProviderOverride(name="openai", model="gpt-test"),
        stages=[
            StageRunRequest(
                stage=BookStage.STRUCTURE,
                prompt="Outline chapters",
                provider_override=stage_override,
            )
        ],
    )
    response = await run_book_flow(payload)
    assert response.provider_name == "mock"
    assert response.stages[0].model == "mock"
    assert response.stages[0].structured_output is not None
    assert response.stages[0].extras == {"critiques": ["Critique: expand middle chapters"] * 3}


async def test_title_stage(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(
        "services.orchestrator.app.flows.ProviderFactory.create",
        lambda config: _StubStructureProvider(),
    )

    payload = RunRequest(
        project_id=uuid4(),
        provider=ProviderOverride(name="mock", model="stub-model"),
        stages=[
            StageRunRequest(
                stage=BookStage.TITLE,
                prompt="A history of administrative innovation across empires",
            )
        ],
    )

    response = await run_book_flow(payload)
    assert response.stages[0].structured_output is not None
    assert "Blueprints" in response.stages[0].output
    assert response.stages[0].extras == {"critique": "Critique: expand middle chapters"}


async def test_research_stage(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(
        "services.orchestrator.app.flows.ProviderFactory.create",
        lambda config: _StubStructureProvider(),
    )

    prompt_payload = json.dumps(
        {
            "synopsis": "Synopsis", 
            "structure_summary": "Foundations and bureaucracy details.",
            "guidelines": "Prioritise primary sources and modern parallels."
        }
    )

    payload = RunRequest(
        project_id=uuid4(),
        provider=ProviderOverride(name="mock", model="stub-model"),
        stages=[
            StageRunRequest(
                stage=BookStage.RESEARCH,
                prompt=prompt_payload,
            )
        ],
    )

    response = await run_book_flow(payload)
    result = response.stages[0]
    assert result.stage == BookStage.RESEARCH
    assert result.structured_output is not None
    assert len(result.structured_output.get("prompts", [])) == 3
    assert result.extras == {"critique": "Critique: expand middle chapters"}


async def test_fact_mapping_stage(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(
        "services.orchestrator.app.flows.ProviderFactory.create",
        lambda config: _StubStructureProvider(),
    )

    project_id = uuid4()
    subchapter_id = uuid4()
    structure_payload = {
        "project_id": str(project_id),
        "version": 1,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "chapters": [
            {
                "id": str(uuid4()),
                "title": "Chapter",
                "summary": "Summary",
                "order": 1,
                "subchapters": [
                    {
                        "id": str(subchapter_id),
                        "title": "Section",
                        "summary": "Details",
                        "order": 1,
                        "learning_objectives": [],
                        "related_subchapters": [],
                    }
                ],
            }
        ],
    }
    candidate_fact = {
        "id": str(uuid4()),
        "project_id": str(project_id),
        "upload_id": 1,
        "prompt_index": 0,
        "source_filename": "doc.docx",
        "summary": "Candidate fact",
        "detail": "Candidate detail",
        "citation": {"source_title": "Doc", "source_type": "other"},
    }
    mapping_payload = {
        "project_id": str(project_id),
        "structure": structure_payload,
        "candidates": [candidate_fact],
    }

    payload = RunRequest(
        project_id=project_id,
        provider=ProviderOverride(name="mock"),
        stages=[
            StageRunRequest(
                stage=BookStage.FACT_MAPPING,
                prompt=json.dumps(mapping_payload),
            )
        ],
    )

    response = await run_book_flow(payload)
    result = response.stages[0]
    assert result.stage == BookStage.FACT_MAPPING
    assert result.structured_output is not None
    assert result.structured_output.get("facts")
    assert result.extras["fact_count"] >= 1


async def test_flow_handles_writing_stage(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    async def fake_generate_writing_batch(payload, run_override, stage_override):
        batch = WritingBatch(
            project_id=uuid4(),
            cycle_count=1,
            readiness="draft",
            summary="Synthetic writing batch",
            total_word_count=512,
            subchapters=[
                SubchapterDraftState(
                    subchapter_id=uuid4(),
                    title="Test",
                    chapter_title="Chapter",
                    order_label="1.1",
                    current_cycle=0,
                    status="draft",
                    iterations=[],
                    outstanding_feedback=[],
                    final_iteration_id=None,
                    final_word_count=None,
                    last_updated=datetime.utcnow(),
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return SimpleNamespace(batch=batch, critique="Mock critique")

    monkeypatch.setattr(
        "services.orchestrator.app.flows.generate_writing_batch",
        fake_generate_writing_batch,
    )

    payload = RunRequest(
        project_id=uuid4(),
        provider=ProviderOverride(name="mock"),
        stages=[
            StageRunRequest(stage=BookStage.WRITING, prompt=json.dumps({"project_id": "demo"})),
        ],
    )

    response = await run_book_flow(payload)
    assert len(response.stages) == 1
    stage_result = response.stages[0]
    assert stage_result.stage == BookStage.WRITING
    assert stage_result.structured_output["cycle_count"] == 1
    assert stage_result.extras == {"critique": "Mock critique"}
