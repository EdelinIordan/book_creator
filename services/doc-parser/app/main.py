"""FastAPI service responsible for parsing uploaded research documents into facts."""

from __future__ import annotations

import base64
import binascii
import io
import logging
from typing import List, Optional

from docx import Document
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from book_creator_observability import (
    log_context,
    setup_fastapi_metrics,
    setup_logging,
)
from book_creator_schemas import ResearchSourceType
from book_creator_schemas.models.book import Citation

app = FastAPI(title="Doc Parser", version="0.2.0")
SERVICE_NAME = "doc_parser"
setup_logging(SERVICE_NAME)
setup_fastapi_metrics(app, service_name=SERVICE_NAME)
logger = logging.getLogger(__name__)


class ParseRequest(BaseModel):
    """Incoming payload containing the document to parse."""

    filename: str = Field(..., min_length=1, max_length=255)
    content_base64: str = Field(..., description="Base64 encoded document content")
    prompt_index: Optional[int] = Field(
        None, ge=0, description="Research prompt index for metadata tracking"
    )


class ParsedFact(BaseModel):
    """Simple representation of a fact extracted from the document."""

    summary: str
    detail: str
    citation: Citation


class ParseResponse(BaseModel):
    """Structured response returned to the API layer."""

    facts: List[ParsedFact] = Field(default_factory=list)
    paragraph_count: int = Field(..., ge=0)
    word_count: int = Field(..., ge=0)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Simple readiness probe."""

    return {"status": "ok"}


@app.post("/parse", response_model=ParseResponse, tags=["parse"])
def parse_document(payload: ParseRequest) -> ParseResponse:
    """Decode the uploaded file, extract paragraphs, and emit candidate facts."""
    with log_context(route="/parse", method="POST"):
        logger.info(
            "Parsing uploaded research document",
            extra={
                "document_filename": payload.filename,
                "prompt_index": getattr(payload, "prompt_index", None),
            },
        )

        try:
            raw_bytes = base64.b64decode(payload.content_base64)
        except (ValueError, binascii.Error) as exc:  # pragma: no cover - rare corrupted payload
            logger.exception("Failed to decode base64 payload")
            raise HTTPException(status_code=400, detail="Invalid base64 encoding") from exc

        if not raw_bytes:
            raise HTTPException(status_code=400, detail="Document content is empty")

        paragraphs = _extract_paragraphs(raw_bytes, payload.filename)
        if not paragraphs:
            logger.info("Document contained no parseable paragraphs")
            return ParseResponse(facts=[], paragraph_count=0, word_count=0)

        facts: list[ParsedFact] = []
        word_total = 0
        for paragraph in paragraphs:
            words = paragraph.split()
            word_total += len(words)
            summary = " ".join(words[:32]).strip()
            if len(words) > 32:
                summary += "..."
            citation = Citation(
                source_title=payload.filename,
                author=None,
                publication_date=None,
                url=None,
                page=None,
                source_type=ResearchSourceType.OTHER,
            )
            facts.append(
                ParsedFact(summary=summary or paragraph[:120], detail=paragraph, citation=citation)
            )

        logger.info(
            "Document parsed successfully",
            extra={
                "paragraph_count": len(paragraphs),
                "fact_count": len(facts),
                "word_count": word_total,
            },
        )
        return ParseResponse(facts=facts, paragraph_count=len(paragraphs), word_count=word_total)


def _extract_paragraphs(raw: bytes, filename: str) -> list[str]:
    """Return cleaned paragraph text for docx and plaintext uploads."""

    name = filename.lower()
    if name.endswith(".docx"):
        with io.BytesIO(raw) as buffer:
            document = Document(buffer)
        paragraphs = [para.text.strip() for para in document.paragraphs if para.text and para.text.strip()]
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="ignore")
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    return [paragraph for paragraph in paragraphs if len(paragraph.split()) >= 3]
