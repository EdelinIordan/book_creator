"""Helpers for parsing embedded JSON blocks within prompts."""

from __future__ import annotations

import json


def extract_json_block(prompt: str, label: str) -> dict:
    """Return the JSON object that follows the given label in a templated prompt."""

    marker = f"{label}: "
    start = prompt.find(marker)
    if start == -1:
        raise ValueError(f"Label '{label}' not found in prompt")

    start += len(marker)
    end = prompt.find("\n", start)
    if end == -1:
        end = len(prompt)

    payload = prompt[start:end].strip()
    if not payload:
        return {}

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Unable to decode JSON for label '{label}'") from exc

