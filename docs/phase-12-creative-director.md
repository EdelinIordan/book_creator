# Phase 12 – Creative Director Guidelines

## Objective
Generate structured writing guidelines for each subchapter through a trio of creative director agents (assistant, critic, final), synthesizing structure, research facts, citations, and emotional cues into actionable briefs for writer agents.

## Scope & Context
- Consumes the fully enriched structure from Phases 10 and 11 plus the finalized book title from Phase 8.
- Guides the tone, pacing, story integration, and factual emphasis for upcoming writing cycles.
- Outputs per-subchapter guideline packets to be used repeatedly by writer, critic, and implementation agents in Phase 13.

- Guideline schema detailing key points: objectives, must-include facts/citations, emotional beats, narrative voice, structural reminders, and success metrics.
- Agent prompts for G1: Assistant Creative Director (initial guidelines), G2: Critic Creative Director (feedback/suggestions), and G3: Final Creative Director (consolidated directive).
- Backend persistence layer storing guideline versions and linking them to subchapters, with status flags for the library dashboard.
- UI checklist view showing guideline content, critique rationale, readiness status, and a summary badge for the category view.

## Milestones & Tasks
1. Build assistant director agent referencing structure, persona, and research to produce initial guidelines per subchapter.
2. Implement critic agent evaluating completeness, tone alignment, and potential pitfalls.
3. Create final director agent that merges feedback and outputs final structured directives.
4. Surface guidelines in frontend with filtering by chapter/subchapter and export options.
5. Update library metadata (e.g., "Guidelines Ready") when final directives are approved.
6. Ensure orchestrator enforces completion of guidelines before writing phase begins.

## Dependencies
- Enriched structure from Phases 10–11.
- Provider adapters (Phase 3) for creative director agents.
- Orchestrator control (Phase 4) to manage stage gating.
- Frontend components (Phase 6/7) for display.

## Risks & Mitigations
- **Risk**: Guidelines become too verbose for writer agents.
  - *Mitigation*: Introduce target length limits and critical bullet prioritisation.
- **Risk**: Critic feedback not integrated properly.
  - *Mitigation*: Validate final directives against critic requirements and flag mismatches.

## Exit Criteria
- Each subchapter has a final, approved guideline packet stored and accessible via API/UI.
- Users can review, edit, or regenerate guidelines before locking the stage.
- Library view reflects guideline readiness and last update time.
- Orchestrator marks stage complete and enables Phase 13 writing pipeline.

## Handoffs & Next Steps
- Provide guideline packets to writer/critic/implementation agents along with structure and facts for Phase 13.
- Capture metrics on guideline iterations to tune prompts later.

## Implementation Notes
- Backend tables `project_guideline_runs` and `project_guideline_packets` persist guideline batches, critique notes, and per-subchapter directives.
- FastAPI endpoints:
  - `GET /projects/{id}/guidelines` loads existing packets (auto-generating them when prerequisites are met).
  - `POST /projects/{id}/guidelines/regenerate` reruns the creative director triad with optional preference notes.
- Orchestrator stage `GUIDELINES` now drives the assistant → critic → final agent sequence, returning `CreativeGuidelineBatch` payloads.
- Story Weave Lab gains a "Guideline Studio" workspace with filtering, readiness badges, and regeneration controls. The dashboard surfaces a "Guidelines Ready" badge once batches are marked ready.
