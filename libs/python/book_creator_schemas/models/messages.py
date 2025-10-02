"""Agent message and critique representations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ..enums import AgentRole, BookStage, CritiqueSeverity


class CritiqueNote(BaseModel):
    """Feedback issued by a critic agent."""

    id: UUID = Field(default_factory=uuid4)
    severity: CritiqueSeverity = CritiqueSeverity.INFO
    summary: str = Field(..., min_length=1, max_length=500)
    details: str = Field(...)
    target_reference: str = Field(
        ..., description="Identifier of the element the critique refers to (chapter, fact, etc.)"
    )
    applied: bool = False


class AgentMessage(BaseModel):
    """Conversation trace for transparency and auditing."""

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    stage: BookStage
    role: AgentRole
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    critiques: list[CritiqueNote] = Field(default_factory=list)
    resulting_artifact_ids: list[UUID] = Field(
        default_factory=list, description="Artifacts produced or updated by this message"
    )

