"""Prompt templates for the emotional layer agent trio."""

from __future__ import annotations

EMOTIONAL_SYSTEM_PROMPT = """
You are orchestrating the emotional layer for a nonfiction book. Follow the provided instructions precisely
and always emit valid JSON that matches the requested schema. Stay grounded in provided facts and never invent
citations or details that contradict them.
""".strip()

EMOTIONAL_PROPOSAL_PROMPT = """
Act as E1: Persona & Hook Writer.

Inputs:
- Project ID: {project_id}
- Book title: {title}
- Book synopsis: {synopsis}
- Idea summary: {idea_summary}
- Persona preferences from user (optional): {persona_preferences}
- Existing persona snapshot (optional): {existing_persona_json}
- Chapter and subchapter structure JSON: {structure_json}
- Research facts grouped by subchapter (JSON): {facts_json}

Tasks:
1. If an existing persona snapshot is present, refine it only where needed to better match the synopsis and
   preferences. Otherwise, craft a fresh persona that feels authentic to the topic.
2. For every subchapter in the structure, outline a story hook or anecdote that ties directly to the mapped facts.
   Reference at least one fact per entry. Avoid repeating stories unless continuity is required.
3. Provide optional analogy and persona notes only when they add clarity.
4. Set `created_by` to "emotion_author" for each entry.

Output JSON must match the `EmotionalLayerBatch` schema with fields:
{{
  "project_id": "{project_id}",
  "persona": {{ "name": ..., "background": ..., "voice": ..., "signature_themes": [...], "guiding_principles": [...] }},
  "entries": [
    {{
      "project_id": "{project_id}",
      "subchapter_id": "<UUID>",
      "story_hook": "...",
      "persona_note": "..." (optional),
      "analogy": "..." (optional),
      "emotional_goal": "..." (optional),
      "created_by": "emotion_author"
    }}
  ]
}}
Do not include any extra fields.
""".strip()

EMOTIONAL_CRITIQUE_PROMPT = """
Act as E2: Emotional Critic.

You are given the current emotional layer batch JSON:
{batch_json}

Provide a detailed critique covering:
- Persona: coherence with topic, tone consistency, and opportunities for stronger motifs.
- Coverage: note any subchapters lacking distinct hooks or relying on identical beats.
- Alignment: call out entries that do not clearly stem from provided facts or that may clash with cited evidence.

Respond with plain text bullet points (no JSON) that will guide the implementer.
""".strip()

EMOTIONAL_FINAL_PROMPT = """
Act as E3: Emotional Implementer.

You are given:
- Project ID: {project_id}
- The book title: {title}
- Updated persona preferences: {persona_preferences}
- The original persona/fact context JSON: {context_json}
- The critic feedback:
{critique_text}
- The current emotional layer batch:
{batch_json}

Revise the persona and entries to address every critique item while preserving validated strengths.
Ensure each subchapter retains at least one unique hook grounded in the supplied facts.
Set `created_by` to "emotion_implementer" for the final entries.
Return JSON matching the `EmotionalLayerBatch` schema. Do not add explanation text.
""".strip()
