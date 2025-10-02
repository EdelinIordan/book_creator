# Phase 11 – Emotional Layer Module

## Objective
Enrich each subchapter with engaging narratives, analogies, and persona-driven storytelling through a tri-agent loop that ensures emotional resonance complements the factual foundation established in Phase 10.

## Scope & Context
- Builds on structure plus fact-mapped subchapters, weaving coherent stories that align with the author persona defined per book.
- Ensures stories, examples, and analogies remain consistent across chapters, avoiding redundancy or contradictions.
- Prepares emotional cues for creative director guidelines (Phase 12) and final writing (Phase 13).

- **Current Implementation Snapshot**
  - Prefect orchestrator now runs the E1→E3 loop via `services/orchestrator/app/emotional/engine.py`, producing a validated `EmotionalLayerBatch` (persona + per-subchapter entries).
  - FastAPI exposes `/projects/{id}/emotional` and `/projects/{id}/emotional/regenerate`, persisting persona snapshots and entries in Postgres and advancing project stage to `GUIDELINES` once complete.
  - The Story Weave Lab UI (`/projects/[id]/emotional`) surfaces persona traits, critique notes, and subchapter hooks with regeneration controls wired through the new API.

- Persona definition template capturing author background, voice, and signature motifs.
- Agent prompts for emotional enrichment via E1: Persona & Hook Writer, E2: Emotional Critic, and E3: Emotional Implementer, each referencing global context and previously written subchapters.
- Consistency checker to flag conflicting narratives or repeated anecdotes.
- UI module (Story Weave) visualising emotional layer contributions with persona timeline, conflict alerts, and status updates for the library.

## Milestones & Tasks
1. Develop persona initialization prompt informed by idea brief, title, and user preferences.
2. Implement enrichment agents with access to entire book context, ensuring stories tie directly to facts and citations where relevant.
3. Build validation routines to detect redundant narratives or mismatched tone.
4. Expose emotional layer editor in frontend with controls to accept, tweak, or regenerate stories per subchapter.
5. Store emotional metadata alongside facts in the structure for later retrieval.
6. Emit stage completion events so the library reflects "Emotional Layer Complete" when all subchapters are approved.

## Dependencies
- Fact-enriched structure from Phase 10.
- Provider abstractions (Phase 3) for storytelling agents.
- Frontend scaffolding from Phase 6 with structure UI from Phase 7.

## Risks & Mitigations
- **Risk**: Emotional content drifts away from factual basis.
  - *Mitigation*: Require agents to reference specific facts/citations and include rationale linking story to data.
- **Risk**: Persona becomes inconsistent across chapters.
  - *Mitigation*: Maintain centralized persona state and run coherence checks before approval.

## Exit Criteria
- Each subchapter includes approved emotional layer entries (intro story, analogies, tone cues) stored with metadata.
- UI highlights any unresolved conflicts; none remain before moving to Phase 12.
- Library dashboard indicates emotional enrichment completion with persona summary tooltip.
- Persona dossier finalized for creative director reference.

## Handoffs & Next Steps
- Deliver enriched structure (facts + emotional cues) to creative director guideline phase.
- Capture user feedback on emotional quality to refine prompts iteratively.
