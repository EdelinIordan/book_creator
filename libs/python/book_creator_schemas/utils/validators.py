"""Reusable validation helpers."""

from __future__ import annotations

from typing import Iterable

from pydantic import ValidationError


class WordCountError(ValueError):
    """Raised when a field exceeds the configured word count."""


def ensure_max_word_count(value: str, *, limit: int, field_name: str) -> str:
    """Validate that the given string does not exceed ``limit`` words.

    Args:
        value: Input text to evaluate.
        limit: Maximum number of words permitted.
        field_name: Name used in the raised error message.

    Returns:
        The original string when validation succeeds.

    Raises:
        WordCountError: If the number of words exceeds the limit.
    """

    word_count = _count_words(value)
    if word_count > limit:
        raise WordCountError(
            f"{field_name} exceeds maximum word count: {word_count} > {limit}"
        )
    return value


def _count_words(value: str) -> int:
    tokens = [token for token in value.strip().split() if token]
    return len(tokens)
