"""Prompt templates for the structure refinement loop."""

from __future__ import annotations

STRUCTURE_SYSTEM_PROMPT = """
You are an expert non-fiction book architect. Given a project idea and context, you
must produce a coherent book structure consisting of chapters and subchapters. The
structure must:
- Cover the core idea comprehensively while avoiding redundancy.
- Provide meaningful summaries for each chapter and subchapter.
- Indicate connections between subchapters where relevant.
Return the structure strictly in the JSON schema provided.
""".strip()


STRUCTURE_PROPOSAL_PROMPT = """
Project idea:
{idea}

Existing context:
{context}

Please draft an initial structure proposal adhering to the JSON schema.
""".strip()


STRUCTURE_CRITIQUE_PROMPT = """
Given the current book structure:
{structure_json}

Provide a concise critique focusing on:
- Missing topics or logical gaps
- Redundant or overlapping sections
- Opportunities to improve narrative flow or cross-linking
Respond with bullet points.
""".strip()


STRUCTURE_IMPROVEMENT_PROMPT = """
You previously proposed this structure:
{structure_json}

Critique feedback:
{critique}

Revise the structure to address the critique while keeping successful sections. Return
only the updated structure in the JSON schema.
""".strip()


FINAL_SUMMARY_PROMPT = """
Summarise the final structure in 4–6 sentences highlighting the narrative arc and key
chapters.
Structure JSON:
{structure_json}
""".strip()
