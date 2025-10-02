"""Prompt templates for research prompt generation."""

from __future__ import annotations

RESEARCH_SYSTEM_PROMPT = """
You are a senior research planner. Given a book outline and context you must produce
three deep-research tasks that an external researcher can execute. Each task should
include:
- A short focus description referencing relevant subchapters.
- The full prompt text to send to a research assistant.
- Suggested source types to prioritise.
- Optional additional notes for nuance or coverage guidance.
Return JSON that matches the provided schema exactly.
""".strip()


RESEARCH_BATCH_PROMPT = """
Book synopsis:
{synopsis}

Structure overview:
{structure_summary}

Author research guidelines:
{guidelines}

Draft three complementary Deep Research prompts covering the major themes above. Make
sure the prompts clearly state expectations for citations and deliverables.
""".strip()


RESEARCH_CRITIQUE_PROMPT = """
Review the following research tasks:
{batch_json}

Identify overlaps, missing coverage, or unclear instructions. Suggest improvements to
focus, source expectations, or deliverables.
""".strip()


RESEARCH_REWRITE_PROMPT = """
Existing research tasks:
{batch_json}

Critique feedback:
{critique}

Write an improved set of three research prompts that incorporates the feedback while
maintaining comprehensive coverage of the book outline.
""".strip()
