# Phase 8 – Title Ideation Flow

## Objective
Implement the agent-driven workflow that transforms the finalized structure into compelling book title options, giving users tools to shortlist, regenerate, and confirm the title that will guide subsequent emotional and writing stages.

## Scope & Context
- Consumes the approved structure from Phase 7 and executes the T1: Titler agent to propose five titles per batch.
- Provides UI for evaluating titles, tracking rationales, and managing shortlist/final selection.
- Sets the official book title, passed downstream to creative director guidelines and writer agents in Phases 12–13.

- Backend title ideation engine (`services/orchestrator/app/title/engine.py`) wrapping provider calls for T1: Titler and returning structured batches plus critique text.
- Orchestrator integration that recognises the `TITLE` stage and stores structured results in `StageRunResult.structured_output`, with the API persisting batches/critique under `project_titles`.
- Title selection UI (`/projects/[id]/titles`) now wired to the live API: users regenerate options, manage shortlist, and confirm the final title.
- Shortlist and final choice persist in Postgres so refreshes and subsequent sessions keep the same decisions.
- Confirming a title advances the project to the RESEARCH stage, pushing status updates back to the dashboard.

## Milestones & Tasks
1. Define prompt template emphasising structure themes, audience, and tone derived from idea brief.
2. Build backend handling for multiple rounds: fetch more options, keep history, enforce maximum attempts.
3. Implement frontend cards comparing titles with rationale and relevance indicators.
4. Allow users to tweak a candidate title manually before finalising.
5. Persist chosen title and broadcast event unlocking Phase 9 research planning while updating library cards with the new title and stage badge (implemented).

## Dependencies
- Final structure artifact from Phase 5/7.
- Provider adapters (Phase 3) for title generation.
- Frontend scaffolding (Phase 6) with structure stage complete (Phase 7).

## Risks & Mitigations
- **Risk**: Generated titles lack variety.
  - *Mitigation*: Use temperature adjustments and optional prompt hints for diversity.
- **Risk**: User loses track of shortlisted titles across regenerations.
  - *Mitigation*: Maintain dedicated shortlist panel with clear status badges.

## Exit Criteria
- Users can generate, review, shortlist, edit, and finalise a title inside the app.
- Selected title stored with project and accessible to creative director and writer stages.
- Library dashboard reflects finalised title and stage advancement to research planning.
- Regeneration limit and cost tracking enforced.

## Handoffs & Next Steps
- Provide finalized title to Phase 9 (research prompt crafting) and Phase 12 (creative director guideline development).
- Record user feedback to refine prompt templates over time.
- Track regeneration counts and LLM cost metrics to inform Phase 16 budgeting work.
