# Phase 5 – Structure Generation Module

## Objective
Implement the seven-agent iterative loop that converts the user’s 100-word idea into a cohesive book structure containing chapters, subchapters, summaries, and cross-linking rationale ready for downstream research and writing stages.

## Scope & Context
- First feature phase to plug into the orchestrator, leveraging schemas, provider adapters, and environment scaffolding from Phases 1–4.
- Covers proposal → critique → improvement cycles across seven agents, ensuring structured JSON output.
- Produces the foundational artifact consumed by Phase 7 UI, Phase 8 title ideation, and all subsequent stages.

- Prompt templates and guardrails for structure agents S1–S7 as defined in `user-app-description-and-agents-roster.md` (Structure Architect, Structural Critics I–III, Structural Editors I–III).
- Prefect-integrated structure engine (`services/orchestrator/app/structure/engine.py`) that orchestrates the S1→S7 proposal/critique/implementation loop and returns a validated `BookStructure` plus per-agent critique notes and summaries.
- Diffing utilities to compare successive structure iterations and highlight changes for the UI (planned for Phase 7).
- Automated validation ensuring chapter/subchapter connectivity and summary completeness.
- API endpoints allowing user oversight (view, accept, request manual edits) before finalising structure.
- Stage transition hooks updating project status from “Idea” to “Structure In Progress/Complete” for the category dashboard.

## Milestones & Tasks
1. Implement agent tasks using provider abstraction and register them within the orchestrator.
2. Create evaluation heuristics (rule-based or smaller LLM) that ensure critiques address coherence and redundancy.
3. Persist each iteration with metadata for later auditing and UI display (initial in-memory stubs, database persistence planned in Phase 7).
4. Add unit/integration tests with mock LLM responses covering edge cases (e.g., excessive subchapters, disconnected topics).
5. Document manual override workflow for users to edit structure and re-run critique loops.
6. Verify status updates propagate to library view upon structure approval and that per-stage LLM overrides (model/temperature) carry through to the structure engine.

## Dependencies
- Orchestrator MVP from Phase 4.
- Schema definitions for book structure from Phase 2.
- Provider adapters from Phase 3 with JSON-enforcement capabilities.

## Risks & Mitigations
- **Risk**: Agents return invalid or repetitive structures.
  - *Mitigation*: Enforce strict schema validation and incorporate critique feedback scoring before accepting iterations.
- **Risk**: User edits break downstream assumptions.
  - *Mitigation*: Re-run validation and offer guidance when manual changes violate structural rules.

## Exit Criteria
- Structure loop completes successfully using real providers (optional) and mock providers (mandatory) with consistent outputs.
- Final structure stored in database, exposing REST/WebSocket endpoints for consumption.
- Library dashboard reflects project status progression once structure is finalised.
- UI receives update events with diffs suitable for Phase 7.

## Handoffs & Next Steps
- Provide structure data contract to Phase 7 for UX implementation and to Phase 8 for title ideation inputs.
- Share evaluation heuristics with later phases to reuse critique scoring patterns.
