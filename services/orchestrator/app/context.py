"""Context trimming helpers to keep prompts within safe token budgets."""

from __future__ import annotations

import os
from typing import Tuple

_DEFAULT_LIMIT = int(os.getenv("CONTEXT_TOKEN_LIMIT", "12000"))


def summarise_prompt(prompt: str, token_limit: int | None = None) -> Tuple[str, bool]:
    """Trim long prompts to stay within the configured soft token limit.

    Args:
        prompt: The original prompt text.
        token_limit: Optional override for the maximum token budget.

    Returns:
        A tuple of ``(possibly_trimmed_prompt, was_trimmed)``.
    """

    if not prompt:
        return prompt, False

    limit = max(token_limit or _DEFAULT_LIMIT, 256)
    # Rough heuristic: 1 token ~ 4 characters for mixed English text.
    approx_tokens = len(prompt) // 4
    if approx_tokens <= limit:
        return prompt, False

    max_chars = limit * 4
    head_length = max_chars // 2
    tail_length = max_chars - head_length

    head = prompt[:head_length].strip()
    tail = prompt[-tail_length:].strip()

    trimmed_prompt = (
        f"[context trimmed to ~{limit} tokens]\n"
        "\n-- begin excerpt --\n"
        f"{head}\n"
        "\n...\n"
        f"{tail}\n"
        "-- end excerpt --"
    )
    return trimmed_prompt, True


__all__ = ["summarise_prompt"]
