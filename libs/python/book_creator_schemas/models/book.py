"""Domain models describing projects, structures, and related artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from ..enums import AgentRole, BookStage, CritiqueSeverity, ResearchSourceType
from ..utils.validators import ensure_max_word_count

UuidStr = Annotated[str, Field(pattern=r"^[a-f0-9-]{36}$")]


class IdeaBrief(BaseModel):
    """Initial concept supplied by the user (max 100 words)."""

    project_id: UUID
    working_title: Optional[str] = Field(None, max_length=150)
    description: str = Field(..., description="Up to 100 words summarising the book")
    audience: Optional[str] = Field(None, max_length=200)
    goals: list[str] = Field(default_factory=list, description="What the author hopes readers achieve")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        return ensure_max_word_count(value, limit=100, field_name="Idea description")


class Subchapter(BaseModel):
    """Smallest structural unit in the book."""

    id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., min_length=1, max_length=1000)
    order: int = Field(..., ge=1)
    learning_objectives: list[str] = Field(default_factory=list)
    related_subchapters: list[UUID] = Field(default_factory=list)


class Chapter(BaseModel):
    """Top-level book chapter containing ordered subchapters."""

    id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., min_length=1, max_length=1200)
    order: int = Field(..., ge=1)
    subchapters: list[Subchapter] = Field(default_factory=list)
    narrative_arc: Optional[str] = Field(None, max_length=1000)


class BookStructure(BaseModel):
    """Full structure for a project with chapter/subchapter hierarchy."""

    project_id: UUID
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    chapters: list[Chapter]
    synopsis: Optional[str] = Field(None, max_length=2000)

    @field_validator("chapters")
    @classmethod
    def validate_ordering(cls, chapters: list[Chapter]) -> list[Chapter]:
        expected_order = list(range(1, len(chapters) + 1))
        actual_order = [chapter.order for chapter in chapters]
        if actual_order != expected_order:
            raise ValueError("Chapter order must be contiguous starting at 1")
        for chapter in chapters:
            sub_expected = list(range(1, len(chapter.subchapters) + 1))
            sub_actual = [sub.order for sub in chapter.subchapters]
            if sub_actual != sub_expected:
                raise ValueError(
                    f"Subchapter order must be contiguous starting at 1 in chapter {chapter.title}"
                )
        return chapters


class ResearchPrompt(BaseModel):
    """Task sent to Deep Research tools."""

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    focus_subchapters: list[UUID] = Field(default_factory=list)
    prompt_text: str = Field(..., min_length=1)
    desired_sources: list[ResearchSourceType] = Field(default_factory=list)
    additional_notes: Optional[str] = Field(None, max_length=1000)
    created_by: AgentRole
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Citation(BaseModel):
    """Attribution for a research fact."""

    source_title: str
    author: Optional[str] = None
    publication_date: Optional[str] = None
    url: Optional[str] = Field(None, max_length=400)
    page: Optional[str] = None
    source_type: ResearchSourceType = ResearchSourceType.OTHER


class ResearchFact(BaseModel):
    """Fact extracted from research material and attached to a subchapter."""

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    subchapter_id: UUID
    upload_id: Optional[int] = None
    prompt_index: Optional[int] = None
    summary: str = Field(..., min_length=1, max_length=800)
    detail: str = Field(...)
    citation: Citation
    redundancy_key: Optional[str] = Field(
        None, description="Hash or identifier to detect duplicates across subchapters"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ResearchFactCandidate(BaseModel):
    """Intermediate fact extracted from an uploaded research document before mapping."""

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    upload_id: Optional[int] = None
    prompt_index: Optional[int] = None
    source_filename: Optional[str] = None
    summary: str = Field(..., min_length=1, max_length=800)
    detail: str = Field(...)
    citation: Citation
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


class PersonaProfile(BaseModel):
    """Author persona information used to ground emotional narratives."""

    name: str = Field(..., min_length=1, max_length=120)
    background: str = Field(..., min_length=1, max_length=1500)
    voice: str = Field(..., min_length=1, max_length=600)
    signature_themes: list[str] = Field(default_factory=list)
    guiding_principles: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EmotionalLayerEntry(BaseModel):
    """Narrative or analogy associated with a subchapter."""

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    subchapter_id: UUID
    story_hook: str = Field(..., min_length=1, max_length=1500)
    persona_note: Optional[str] = Field(None, max_length=500)
    analogy: Optional[str] = Field(None, max_length=1000)
    emotional_goal: Optional[str] = Field(None, max_length=400)
    created_by: AgentRole
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EmotionalLayerBatch(BaseModel):
    """Container returned by emotional layer agents."""

    project_id: UUID
    persona: PersonaProfile
    entries: list[EmotionalLayerEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GuidelineFactReference(BaseModel):
    """Instruction to include a specific research fact in the draft."""

    fact_id: UUID
    summary: str = Field(..., min_length=1, max_length=600)
    citation: Citation
    rationale: Optional[str] = Field(
        None,
        max_length=400,
        description="Quick explanation of why the fact matters for the draft",
    )


class CreativeGuideline(BaseModel):
    """Structured directive provided before writing a subchapter."""

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    subchapter_id: UUID
    objectives: list[str] = Field(
        default_factory=list,
        min_length=1,
        description="Primary outcomes the draft must achieve",
    )
    must_include_facts: list[GuidelineFactReference] = Field(
        default_factory=list,
        description="Facts and citations the draft must reference",
    )
    emotional_beats: list[str] = Field(
        default_factory=list,
        description="Key emotional moments or anecdotes to weave in",
    )
    narrative_voice: Optional[str] = Field(
        None,
        max_length=400,
        description="Voice guidance synthesising persona cues",
    )
    structural_reminders: list[str] = Field(
        default_factory=list,
        description="Calls to keep chapter flow and callbacks consistent",
    )
    success_metrics: list[str] = Field(
        default_factory=list,
        description="Checklist used to confirm the draft meets expectations",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Potential pitfalls to avoid while drafting",
    )
    status: Literal["draft", "final", "needs_review"] = Field(
        default="final",
        description="Readiness of the guideline packet",
    )
    created_by: AgentRole
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None


class CreativeGuidelineBatch(BaseModel):
    """Collection of guideline packets for a project run."""

    project_id: UUID
    version: int = Field(default=1, ge=1)
    summary: Optional[str] = Field(
        None,
        max_length=2000,
        description="High-level guidance for the writing team",
    )
    readiness: Literal["draft", "ready"] = Field(default="draft")
    guidelines: list[CreativeGuideline] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None


class DraftVersion(BaseModel):
    """One iteration of a written subchapter."""

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    subchapter_id: UUID
    version_index: int = Field(..., ge=0)
    role: AgentRole = Field(..., description="Agent responsible for this draft")
    content: str
    linked_critiques: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectProgressSnapshot(BaseModel):
    """Aggregated project status for dashboard summaries."""

    project_id: UUID
    stage: BookStage
    percent_complete: float = Field(..., ge=0, le=100)
    completed_stages: list[BookStage] = Field(default_factory=list)
    total_subchapters: int = Field(..., ge=0)
    completed_subchapters: int = Field(..., ge=0)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("completed_subchapters")
    @classmethod
    def validate_subchapter_progress(cls, completed: int, info) -> int:
        total = info.data.get("total_subchapters", 0)
        if completed > total:
            raise ValueError("Completed subchapters cannot exceed total subchapters")
        return completed


class TitleOption(BaseModel):
    """Single title suggestion with rationale."""

    title: str = Field(..., min_length=2, max_length=120)
    rationale: str = Field(..., min_length=2, max_length=400)


class TitleBatch(BaseModel):
    """Collection of title options returned by ideation agents."""

    options: list[TitleOption] = Field(..., min_items=1, max_items=10)


class SubchapterFactCoverage(BaseModel):
    """Coverage summary produced after fact mapping."""

    subchapter_id: UUID
    fact_count: int = Field(..., ge=0)


class FactMappingBatch(BaseModel):
    """Structured payload describing mapped research facts per subchapter."""

    project_id: UUID
    facts: list[ResearchFact] = Field(default_factory=list)
    coverage: list[SubchapterFactCoverage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DraftFeedbackItem(BaseModel):
    """Actionable feedback supplied by critic agents during writing."""

    id: UUID = Field(default_factory=uuid4)
    message: str = Field(..., min_length=1, max_length=600)
    severity: CritiqueSeverity = Field(default=CritiqueSeverity.WARNING)
    category: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional focus area such as structure, evidence, or tone.",
    )
    rationale: Optional[str] = Field(
        None,
        max_length=600,
        description="Additional context explaining the feedback item.",
    )
    addressed: bool = Field(
        default=False,
        description="True once an implementation iteration resolves this item.",
    )
    addressed_in_iteration: Optional[UUID] = Field(
        None,
        description="Iteration identifier that satisfied this feedback item.",
    )


class DraftIteration(BaseModel):
    """Single step within the seven-agent writing loop."""

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    subchapter_id: UUID
    cycle: int = Field(
        ...,
        ge=0,
        description="0 for the initial writer pass, increasing with each critique cycle.",
    )
    role: AgentRole
    content: str = Field(..., min_length=1)
    summary: Optional[str] = Field(
        None,
        max_length=600,
        description="Short highlight of changes or intent for this iteration.",
    )
    word_count: Optional[int] = Field(None, ge=0)
    feedback: list[DraftFeedbackItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SubchapterDraftState(BaseModel):
    """Aggregated writing state for a specific subchapter."""

    subchapter_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    chapter_title: Optional[str] = Field(None, max_length=200)
    order_label: Optional[str] = Field(
        None,
        description="Display order e.g. '2.3' combining chapter and subchapter indices.",
    )
    current_cycle: int = Field(default=0, ge=0)
    status: Literal["draft", "in_review", "ready"] = Field(default="draft")
    iterations: list[DraftIteration] = Field(default_factory=list)
    outstanding_feedback: list[DraftFeedbackItem] = Field(default_factory=list)
    final_iteration_id: Optional[UUID] = None
    final_word_count: Optional[int] = Field(None, ge=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class WritingBatch(BaseModel):
    """Payload returned from the orchestrated writing workflow."""

    project_id: UUID
    cycle_count: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Number of critique/implementation cycles completed by the orchestrator.",
    )
    readiness: Literal["draft", "ready"] = Field(default="draft")
    summary: Optional[str] = Field(
        None,
        max_length=2000,
        description="Narrative summary or key decisions captured during the run.",
    )
    subchapters: list[SubchapterDraftState] = Field(default_factory=list)
    total_word_count: Optional[int] = Field(None, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
