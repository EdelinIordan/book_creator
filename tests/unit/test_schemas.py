"""Smoke tests for Pydantic schema validation."""

from uuid import uuid4

from book_creator_schemas import (
    AgentMessage,
    AgentRole,
    BookStage,
    BookStructure,
    Chapter,
    CreativeGuideline,
    CreativeGuidelineBatch,
    CritiqueNote,
    DraftVersion,
    EmotionalLayerBatch,
    EmotionalLayerEntry,
    FactMappingBatch,
    GuidelineFactReference,
    IdeaBrief,
    PersonaProfile,
    ProjectProgressSnapshot,
    ResearchFact,
    ResearchPrompt,
    Subchapter,
    SubchapterFactCoverage,
)


def test_book_structure_orders_validate() -> None:
    chapter = Chapter(
        title="Sample",
        summary="Summary",
        order=1,
        subchapters=[
            Subchapter(title="One", summary="Summary", order=1),
            Subchapter(title="Two", summary="Summary", order=2),
        ],
    )
    structure = BookStructure(project_id=uuid4(), chapters=[chapter])
    assert structure.chapters[0].subchapters[0].title == "One"


def test_research_prompt_accepts_sources() -> None:
    prompt = ResearchPrompt(
        project_id=uuid4(),
        prompt_text="Investigate logistics records",
        desired_sources=["academic_journal"],
        created_by=AgentRole.RESEARCH_PLANNER,
    )
    assert prompt.desired_sources == ["academic_journal"]


def test_agent_message_with_critique() -> None:
    note = CritiqueNote(
        severity="warning",
        summary="Duplicate fact",
        details="Matches earlier logistics insight",
        target_reference="subchapter:1",
    )
    message = AgentMessage(
        project_id=uuid4(),
        stage=BookStage.FACT_MAPPING,
        role=AgentRole.FACT_CRITIC,
        content="Identify duplicates",
        critiques=[note],
    )
    assert message.critiques[0].severity.value == "warning"


def test_progress_snapshot_progress_bounds() -> None:
    snapshot = ProjectProgressSnapshot(
        project_id=uuid4(),
        stage=BookStage.STRUCTURE,
        percent_complete=25.0,
        total_subchapters=4,
        completed_subchapters=1,
    )
    assert snapshot.percent_complete == 25.0


def test_emotional_layer_entry_allows_optional_fields() -> None:
    entry = EmotionalLayerEntry(
        project_id=uuid4(),
        subchapter_id=uuid4(),
        story_hook="A childhood anecdote introduces the concept.",
        created_by=AgentRole.EMOTION_AUTHOR,
    )
    assert entry.persona_note is None


def test_emotional_layer_batch_wraps_entries() -> None:
    project_id = uuid4()
    subchapter_id = uuid4()
    persona = PersonaProfile(
        name="Dr. Elara Quinn",
        background="A neuroscientist turned educator who connects brain science to everyday routines.",
        voice="Warm, inquisitive, and lightly humorous without losing credibility.",
        signature_themes=["curiosity", "resilience"],
        guiding_principles=["Make science relatable", "Ground stories in evidence"],
    )
    entry = EmotionalLayerEntry(
        project_id=project_id,
        subchapter_id=subchapter_id,
        story_hook="Elara recalls misreading MRI data early in her career.",
        created_by=AgentRole.EMOTION_IMPLEMENTER,
    )
    batch = EmotionalLayerBatch(project_id=project_id, persona=persona, entries=[entry])
    assert batch.entries[0].subchapter_id == subchapter_id


def test_draft_version_records_role() -> None:
    draft = DraftVersion(
        project_id=uuid4(),
        subchapter_id=uuid4(),
        version_index=0,
        role=AgentRole.WRITER,
        content="First draft",
    )
    assert draft.role == AgentRole.WRITER


def test_creative_guideline_handles_fact_references() -> None:
    fact_id = uuid4()
    guideline = CreativeGuideline(
        project_id=uuid4(),
        subchapter_id=uuid4(),
        objectives=["Clarify supply chain leverage"],
        must_include_facts=[
            GuidelineFactReference(
                fact_id=fact_id,
                summary="Global inventory turnover improved by 18% year-over-year.",
                citation={"source_title": "Logistics Review", "source_type": "academic_journal"},
                rationale="Demonstrates measurable impact of the recommended framework.",
            )
        ],
        emotional_beats=["Open with the founder's near-failure anecdote."],
        narrative_voice="Confident mentor with pragmatic optimism.",
        structural_reminders=["Call back to Chapter 2's systems map."],
        success_metrics=["Reader can summarise the three-lever model without notes."],
        created_by=AgentRole.CREATIVE_DIRECTOR_FINAL,
        status="final",
        version=2,
    )
    assert guideline.must_include_facts[0].fact_id == fact_id


def test_creative_guideline_batch_wraps_packets() -> None:
    guideline = CreativeGuideline(
        project_id=uuid4(),
        subchapter_id=uuid4(),
        objectives=["Help readers audit their workflow"],
        must_include_facts=[],
        emotional_beats=["Celebrate small operational wins."],
        structural_reminders=["Reference earlier diagnostic checklist."],
        success_metrics=["Draft lists two actionable experiments."],
        created_by=AgentRole.CREATIVE_DIRECTOR_FINAL,
    )
    batch = CreativeGuidelineBatch(project_id=guideline.project_id, guidelines=[guideline], readiness="ready")
    assert batch.guidelines[0].project_id == guideline.project_id


def test_research_fact_requires_citation() -> None:
    fact = ResearchFact(
        project_id=uuid4(),
        subchapter_id=uuid4(),
        summary="Logistics surplus of 15%",
        detail="Records show surplus",
        citation={
            "source_title": "Harvests of Power",
            "source_type": "academic_journal",
        },
    )
    assert fact.citation.source_title == "Harvests of Power"


def test_idea_brief_word_count_limit() -> None:
    idea = IdeaBrief(
        project_id=uuid4(),
        description="Concise idea describing the book vision.",
    )
    assert "book" in idea.description


def test_agent_message_allows_resulting_artifacts() -> None:
    message = AgentMessage(
        project_id=uuid4(),
        stage=BookStage.WRITING,
        role=AgentRole.IMPLEMENTATION,
        content="Applied critic feedback",
        resulting_artifact_ids=[uuid4()],
    )
    assert len(message.resulting_artifact_ids) == 1


def test_fact_mapping_batch_serialises() -> None:
    project_id = uuid4()
    subchapter_id = uuid4()
    batch = FactMappingBatch(
        project_id=project_id,
        facts=[
            ResearchFact(
                project_id=project_id,
                subchapter_id=subchapter_id,
                upload_id=1,
                prompt_index=0,
                summary="Key logistics insight",
                detail="Detailed fact text",
                citation={"source_title": "Doc", "source_type": "other"},
            )
        ],
        coverage=[SubchapterFactCoverage(subchapter_id=subchapter_id, fact_count=1)],
    )
    assert batch.coverage[0].fact_count == 1
