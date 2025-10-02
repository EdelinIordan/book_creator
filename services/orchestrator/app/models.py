"""Pydantic models for orchestrator API."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from book_creator_schemas import BookStage


class ProviderOverride(BaseModel):
    name: Optional[str] = Field(
        None, description="Provider identifier: gemini, openai, mock"
    )
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_output_tokens: Optional[int] = Field(None, ge=16)
    json_mode: Optional[bool] = None
    top_p: Optional[float] = Field(None, ge=0, le=1)
    reasoning_effort: Optional[str] = Field(
        None,
        description="OpenAI GPT-5 reasoning effort (minimal, low, medium, high)",
    )
    verbosity: Optional[str] = Field(
        None, description="OpenAI GPT-5 verbosity (low, medium, high)"
    )
    thinking_budget: Optional[int] = Field(
        None,
        description="Gemini 2.5 thinking budget in tokens; -1 enables dynamic thinking",
    )
    include_thoughts: Optional[bool] = Field(
        None, description="Gemini 2.5 thought summaries toggle"
    )


class StageRunRequest(BaseModel):
    stage: BookStage
    prompt: str = Field(..., min_length=1)
    provider_override: ProviderOverride | None = None


class RunRequest(BaseModel):
    project_id: Optional[UUID] = None
    provider: ProviderOverride | None = None
    stages: List[StageRunRequest] = Field(default_factory=list)


class StageRunResult(BaseModel):
    stage: BookStage
    output: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float | None = None
    cost_usd: float | None = None
    received_at: datetime
    structured_output: dict | None = None
    extras: dict | None = None


class RunResponse(BaseModel):
    run_id: UUID
    provider_name: str
    stages: List[StageRunResult]
    created_at: datetime = Field(default_factory=datetime.utcnow)
