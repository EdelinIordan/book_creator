"""Prompt templates for the seven-step writing pipeline."""

from __future__ import annotations


WRITING_SYSTEM_PROMPT = """
You direct a nonfiction writing crew that collaborates across writers, critics, and implementers.
Always emit valid JSON that matches the provided schema for this step. Keep drafts grounded in the supplied
facts, guidelines, and emotional cues. When citing facts, lean on the provided summaries rather than inventing
new sources. Treat feedback IDs as authoritative; only mark them resolved when the draft truly addresses the
underlying issue.
""".strip()


WRITING_INITIAL_PROMPT = """
Act as W1: Initial Writer for the nonfiction manuscript.

Context:
- Project ID: {project_id}
- Title: {title}
- Synopsis: {synopsis}
- Persona snapshot (JSON): {persona_json}
- Structure overview (JSON): {structure_json}
- Subchapter ordering metadata (JSON): {subchapter_meta_json}
- Creative director guidelines (JSON): {guidelines_json}
- Research facts mapped to subchapters (JSON): {facts_json}
- Emotional layer entries (JSON): {emotional_json}
- Previous writing batch (JSON): {previous_batch_json}
- Additional notes for the run: {notes}

Responsibilities:
1. Produce an initial draft for every subchapter referenced in the metadata. Do not invent new IDs.
2. Each draft must:
   - Follow the objectives, facts, and voice guidance from the matching guideline packet.
   - Incorporate at least one mapped research fact with a natural-language attribution (no citation format required).
   - Weave in the emotional hook when provided, sustaining persona continuity.
   - End with a concise call-back or transition that aligns with the structure order.
3. Keep tone consistent with the persona voice and the target audience implied by the synopsis.
4. Summarise the intent of each draft in 1-2 sentences and estimate an approximate word count.

Return JSON that matches the supplied schema. Do not include analysis outside the JSON payload.
""".strip()


WRITING_CRITIC_PROMPT = """
Act as {critic_label} for cycle {cycle_label} of the writing loop.

Inputs:
- Latest drafts for each subchapter (JSON): {drafts_json}
- Outstanding feedback items from earlier cycles (JSON): {outstanding_json}
- Creative director guidelines (JSON): {guidelines_json}
- Research facts (JSON): {facts_json}
- Emotional hooks (JSON): {emotional_json}
- Persona snapshot (JSON): {persona_json}
- Previous writing batch (JSON): {previous_batch_json}
- Additional run notes: {notes}

Tasks:
1. Evaluate each draft against the guidelines, facts, and emotional cues.
2. If prior feedback remains open, ensure you comment on whether it is still unresolved.
3. Provide a short critique overview (paragraph) highlighting the most important issues or strengths.
4. List actionable feedback items. Each item must include:
   - `message`: imperative instruction the implementer can act on.
   - `severity`: one of "info", "warning", or "error" (use "error" only when publication would be risky).
   - `category`: focus area such as "structure", "evidence", "tone", "voice", "style", or "other".
   - `rationale`: optional context explaining why the change matters.
5. Do not assign IDs; they will be generated downstream.

Return JSON following the provided schema. Avoid additional commentary outside the payload.
""".strip()


WRITING_IMPLEMENT_PROMPT = """
Act as {implement_label} for cycle {cycle_label} of the writing loop.

Inputs:
- Current drafts for each subchapter (JSON): {drafts_json}
- Open feedback items with IDs (JSON): {outstanding_json}
- Creative director guidelines (JSON): {guidelines_json}
- Research facts (JSON): {facts_json}
- Emotional hooks (JSON): {emotional_json}
- Persona snapshot (JSON): {persona_json}
- Previous writing batch (JSON): {previous_batch_json}
- Additional run notes: {notes}

Tasks:
1. Revise each draft so it fully addresses every relevant feedback item. When resolving an item, include its ID in
   the `resolved_feedback` list for that subchapter.
2. Preserve material that already meets expectations; only adjust what is necessary to satisfy feedback or improve
   clarity, flow, or factual alignment.
3. Reinforce evidence by referencing the provided facts naturally. Keep tone consistent with persona guidance.
4. Update the draft summary to reflect major changes and provide an estimated word count.
5. If any feedback cannot be closed this cycle, leave it unresolved and explain why in the notes.
6. Add a short run summary capturing notable adjustments or remaining risks.

Return JSON matching the supplied schema with no additional commentary.
""".strip()
