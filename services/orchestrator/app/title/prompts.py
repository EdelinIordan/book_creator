"""Prompts used for title ideation workflow."""

from __future__ import annotations

TITLE_SYSTEM_PROMPT = """
You are a creative director who crafts compelling nonfiction book titles. Titles must be
concise (max 12 words), memorable, and aligned with the book's core themes. Provide a short
rationale for each suggestion.
""".strip()

TITLE_BATCH_PROMPT = """
Book structure synopsis:
{synopsis}

Key chapters:
{chapters}

Target audience and tone:
{audience}

Please propose five title options. Respond using the provided JSON schema.
""".strip()

TITLE_CRITIQUE_PROMPT = """
Given the following titles and rationales:
{titles_json}

Evaluate diversity, clarity, and audience fit. Suggest improvements if titles overlap or
miss the core promise.
""".strip()

TITLE_REWRITE_PROMPT = """
Earlier suggestions:
{titles_json}

Critique feedback:
{critique}

Generate five improved title options. Blend the strongest ideas and introduce new angles.
Return JSON using the provided schema.
""".strip()
