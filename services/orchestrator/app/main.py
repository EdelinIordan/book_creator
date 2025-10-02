"""FastAPI entrypoint for the Prefect-powered orchestrator."""

from __future__ import annotations

import logging
from typing import List

from fastapi import FastAPI

from book_creator_observability import (
    log_context,
    setup_fastapi_metrics,
    setup_logging,
)

from .flows import run_book_flow
from .models import RunRequest, RunResponse, StageRunRequest
from .stages import DEFAULT_STAGE_PROMPTS

SERVICE_NAME = "orchestrator"
setup_logging(SERVICE_NAME)
logger = logging.getLogger(__name__)

app = FastAPI(title="Book Creator Orchestrator", version="0.2.0")
setup_fastapi_metrics(app, service_name=SERVICE_NAME)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/stages/defaults", tags=["orchestrator"])
async def default_stages() -> List[StageRunRequest]:
    return [StageRunRequest(stage=stage, prompt=prompt) for stage, prompt in DEFAULT_STAGE_PROMPTS.items()]


@app.post("/orchestrator/run", response_model=RunResponse, tags=["orchestrator"])
async def orchestrate(payload: RunRequest) -> RunResponse:
    if not payload.stages:
        payload.stages = [StageRunRequest(stage=stage, prompt=prompt) for stage, prompt in DEFAULT_STAGE_PROMPTS.items()]
    project_context = {}
    if payload.project_id:
        project_context["project_id"] = str(payload.project_id)

    with log_context(stage="pipeline", **project_context):
        logger.info(
            "Dispatching orchestrator run",
            extra={"stage_count": len(payload.stages)},
        )

    response = await run_book_flow(payload)

    with log_context(run_id=str(response.run_id), **project_context):
        logger.info(
            "Completed orchestrator run",
            extra={
                "stage_count": len(response.stages),
                "provider": response.provider_name,
            },
        )

    return response
