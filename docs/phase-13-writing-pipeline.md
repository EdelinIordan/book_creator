# Phase 13 – Writing Pipeline

## Objective
Operationalize the seven-step writing loop that produces polished subchapter drafts by iterating between writer, critic, and implementation agents, adhering to guidelines, facts, citations, and emotional cues gathered in earlier phases.

## Scope & Context
- Core production stage drawing on every prior artifact: structure (Phase 5/7), facts (Phase 10), emotional layer (Phase 11), guidelines (Phase 12), and title (Phase 8).
- Consists of the W1 → W7 sequence: W1 Initial Writer draft, W2 Critical Reviewer I, W3 Implementation I, W4 Critical Reviewer II, W5 Implementation II, W6 Critical Reviewer III, and W7 Implementation III.
- Supports version tracking, diffing, and user approvals across iterations.

- Agent prompts for W1–W7 roles with adherence checks to guidelines and citations.
- Draft storage schema capturing each iteration, feedback items, acceptance status, and progress metrics surfaced to the library (e.g., current cycle number).
- Quality checks ensuring critic feedback is fully addressed in subsequent implementation.
- Frontend Writing Studio with diff viewer, feedback checklist, acceptance controls, export options (Markdown/DOCX), and stage badges synced to the library view.

## Milestones & Tasks
1. Implement sequential agent tasks using orchestrator state machine, ensuring each receives latest draft and critique context.
2. Develop feedback tracking model linking critic suggestions to implementation confirmation.
3. Integrate plagiarism/similarity checks (optional) to ensure originality and proper citation usage.
4. Enable user intervention: editing drafts directly, adding manual notes, or requesting additional cycles if needed.
5. Update library progress (e.g., "Writing Cycle 2 of 3", word count, completion percentage) after each iteration.
6. Provide export pipeline bundling final manuscript with bibliography.

## Dependencies
- Creative director guidelines (Phase 12).
- Provider adapters (Phase 3) for long-form generation and critique.
- Frontend infrastructure (Phase 6) with enhancements from earlier UX phases.
- Observability hooks (Phase 15) for monitoring cost/latency due to heavy LLM usage.

## Risks & Mitigations
- **Risk**: Drafts diverge from guidelines or facts.
  - *Mitigation*: Implement automatic checks referencing guidelines and fact citations before accepting drafts.
- **Risk**: Cost/time explosion from seven cycles.
  - *Mitigation*: Allow configuration of cycle count and provide early accept options when quality is high.

## Exit Criteria
- Each subchapter achieves final draft status after passing through up to seven stages, with audit trail of critiques and implementations.
- Users can review diffs, confirm completion, and export compiled chapters.
- Library dashboard reflects writing completion, word count, and export availability.
- Stage completion triggers final manuscript assembly for QA and release planning.

## Handoffs & Next Steps
- Supply final manuscript to Phase 14 for QA and to Phase 18 for documentation/polish activities.
- Capture metrics on cycle counts to inform future optimizations.

## Implementation Notes
- Backend persistence now uses `project_writing_runs` and `project_writing_iterations` to store the latest `WritingBatch` plus per-iteration snapshots, keeping critic feedback history in sync with the UI.
- FastAPI exposes `GET /projects/{id}/writing` and `POST /projects/{id}/writing/run` to orchestrate the seven-agent loop and surface batch metadata.
- The orchestrator writing engine coordinates writers, critics, and implementers in sequence, returning structured payloads that track outstanding feedback, cycle counts, and draft readiness.
- Story Weave Lab includes a dedicated Writing Studio with timeline views, outstanding feedback badges, and rerun controls tied to the new endpoints.
