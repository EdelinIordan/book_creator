"""Tests for the FastAPI research upload pipeline."""

from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from book_creator_schemas.enums import BookStage

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/book_creator_test",
)

import psycopg_pool


class _StubConnectionPool:
    def __init__(self, *args, **kwargs) -> None:  # noqa: D401 - simple stub
        self.conninfo = kwargs.get("conninfo") if "conninfo" in kwargs else args[0] if args else None

    def connection(self, *args, **kwargs):  # pragma: no cover - should not be used in these tests
        raise RuntimeError("Database access is not available in unit tests")


psycopg_pool.ConnectionPool = _StubConnectionPool  # type: ignore[attr-defined]

from apps.api.app.main import (
    ProjectSummary,
    ResearchDetail,
    ResearchPromptModel,
    ResearchUploadModel,
    ResearchUploadRequest,
    _handle_research_upload,
)


def _encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_handle_research_upload_triggers_fact_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid4()
    uploaded_bytes: dict[str, bytes] = {}
    parse_payload = {
        "facts": [
            {
                "summary": "Logistics reforms enabled faster grain delivery.",
                "detail": "Logistics reforms enabled faster grain delivery across the empire.",
                "citation": {"source_title": "research-notes.txt"},
            }
        ],
        "word_count": 9,
        "paragraph_count": 1,
    }

    detail = ResearchDetail(
        project=ProjectSummary(
            id=project_id,
            title="Logistics of Empire",
            stage=BookStage.RESEARCH,
            stage_label="Research",
            progress=45,
            idea_summary="",
            research_guidelines=None,
            last_updated=datetime.now(timezone.utc),
            category=None,
            guidelines_ready=False,
            guideline_version=None,
            guideline_updated_at=None,
            writing_ready=False,
            writing_updated_at=None,
        ),
        prompts=[
            ResearchPromptModel(
                focus_summary="Logistics reforms",
                focus_subchapters=["1.1"],
                prompt_text="Investigate reforms",
                desired_sources=["academic_journal"],
                additional_notes=None,
            )
        ],
        critique=None,
        guidelines=None,
        uploads=[
            ResearchUploadModel(
                id=1,
                prompt_index=0,
                filename="research-notes.txt",
                storage_path="/tmp/research-notes.txt",
                notes=None,
                uploaded_at=datetime.now(timezone.utc),
                word_count=9,
                paragraph_count=1,
            )
        ],
    )

    async def immediate(func, *args, **kwargs):  # type: ignore[override]
        return func(*args, **kwargs)

    monkeypatch.setattr("apps.api.app.main.run_in_threadpool", immediate)

    def fake_save(project, prompt_index, filename, content):
        uploaded_bytes["content"] = content
        return "/tmp/path", filename

    async def fake_parse(filename, content_base64, prompt_index):
        assert filename == "research-notes.txt"
        assert content_base64 == _encode(b"grain delivery")
        assert prompt_index == 0
        return parse_payload

    def fake_record(project, prompt_index, filename, storage_path, notes, parse_result):
        assert parse_result == parse_payload
        return True

    stage_triggered = {"value": False}

    async def fake_run_fact_mapping(project):
        stage_triggered["value"] = True

    def fake_fetch_detail(project):
        return detail

    monkeypatch.setattr("apps.api.app.main._save_research_upload_file", fake_save)
    monkeypatch.setattr("apps.api.app.main._parse_research_document", fake_parse)
    monkeypatch.setattr("apps.api.app.main._record_research_upload", fake_record)
    monkeypatch.setattr("apps.api.app.main._run_fact_mapping_stage", fake_run_fact_mapping)
    monkeypatch.setattr("apps.api.app.main._fetch_research_detail", fake_fetch_detail)

    payload = ResearchUploadRequest(
        prompt_index=0,
        filename="research-notes.txt",
        content_base64=_encode(b"grain delivery"),
        notes=None,
    )

    result = await _handle_research_upload(project_id, payload)

    assert uploaded_bytes["content"] == b"grain delivery"
    assert stage_triggered["value"] is True
    assert result is detail


async def test_handle_research_upload_propagates_invalid_base64(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid4()

    async def immediate(func, *args, **kwargs):  # type: ignore[override]
        return func(*args, **kwargs)

    monkeypatch.setattr("apps.api.app.main.run_in_threadpool", immediate)

    payload = ResearchUploadRequest(
        prompt_index=0,
        filename="bad.txt",
        content_base64="not-base64",
    )

    with pytest.raises(HTTPException) as exc:
        await _handle_research_upload(project_id, payload)

    assert "encoding" in exc.value.detail


async def test_handle_research_upload_skips_fact_mapping_when_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    parse_payload = {"facts": [], "word_count": 0, "paragraph_count": 0}

    detail = ResearchDetail(
        project=ProjectSummary(
            id=project_id,
            title="Logistics of Empire",
            stage=BookStage.RESEARCH,
            stage_label="Research",
            progress=45,
            idea_summary="",
            research_guidelines=None,
            last_updated=datetime.now(timezone.utc),
            category=None,
            guidelines_ready=False,
            guideline_version=None,
            guideline_updated_at=None,
            writing_ready=False,
            writing_updated_at=None,
        ),
        prompts=[],
        critique=None,
        guidelines=None,
        uploads=[],
    )

    async def immediate(func, *args, **kwargs):  # type: ignore[override]
        return func(*args, **kwargs)

    monkeypatch.setattr("apps.api.app.main.run_in_threadpool", immediate)

    monkeypatch.setattr(
        "apps.api.app.main._save_research_upload_file",
        lambda *args, **kwargs: ("/tmp/path", "doc.txt"),
    )

    async def fake_parse(filename, content_base64, prompt_index):
        return parse_payload

    def fake_record(*args, **kwargs):
        return False

    stage_triggered = {"value": False}

    async def fake_run_fact_mapping(project):
        stage_triggered["value"] = True

    monkeypatch.setattr("apps.api.app.main._parse_research_document", fake_parse)
    monkeypatch.setattr("apps.api.app.main._record_research_upload", fake_record)
    monkeypatch.setattr("apps.api.app.main._run_fact_mapping_stage", fake_run_fact_mapping)
    monkeypatch.setattr("apps.api.app.main._fetch_research_detail", lambda _: detail)

    payload = ResearchUploadRequest(
        prompt_index=0,
        filename="doc.txt",
        content_base64=_encode(b"placeholder"),
    )

    result = await _handle_research_upload(project_id, payload)

    assert result is detail
    assert stage_triggered["value"] is False
