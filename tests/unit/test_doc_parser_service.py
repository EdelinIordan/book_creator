"""Tests for the research document parsing microservice."""

from __future__ import annotations

import base64

import pytest
import importlib.util
from pathlib import Path
from typing import List, Optional

import docx  # noqa: F401  # Ensure dependency is available before dynamic import

DOC_PARSER_MAIN = (
    Path(__file__).resolve().parents[2] / "services" / "doc-parser" / "app" / "main.py"
)
MODULE_NAME = "doc_parser_under_test"

SPEC = importlib.util.spec_from_file_location(MODULE_NAME, DOC_PARSER_MAIN)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Failed to load doc parser module for testing")
doc_parser = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doc_parser)

HTTPException = doc_parser.HTTPException
parse_document = doc_parser.parse_document

doc_parser.ParseRequest.model_rebuild(_types_namespace={"Optional": Optional})
doc_parser.ParsedFact.model_rebuild(_types_namespace={"Citation": doc_parser.Citation})
doc_parser.ParseResponse.model_rebuild(
    _types_namespace={"List": List, "ParsedFact": doc_parser.ParsedFact}
)


class _RequestStub:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)


def _encode_text(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def test_parse_plaintext_document_emits_facts() -> None:
    payload = _RequestStub(
        filename="research-notes.txt",
        content_base64=_encode_text(
            "Logistics reforms enabled faster grain delivery.\n\n"
            "New canal projects reduced costs across the empire."
        ),
        prompt_index=1,
    )

    response = parse_document(payload)

    assert response.word_count >= 13
    assert response.paragraph_count == 2
    assert len(response.facts) == 2
    assert response.facts[0].summary.startswith("Logistics reforms enabled")
    assert response.facts[0].citation.source_title == "research-notes.txt"


def test_parse_document_rejects_empty_payload() -> None:
    payload = _RequestStub(filename="empty.txt", content_base64=_encode_text(""))

    with pytest.raises(HTTPException) as exc:
        parse_document(payload)

    assert exc.value.status_code == 400
    assert "empty" in exc.value.detail.lower()


def test_parse_document_errors_on_invalid_base64() -> None:
    payload = _RequestStub(filename="invalid.txt", content_base64="!!!")

    with pytest.raises(HTTPException) as exc:
        parse_document(payload)

    assert exc.value.status_code == 400
    assert "empty" in exc.value.detail.lower()
