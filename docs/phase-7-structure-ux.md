# Phase 7 – Structure UX Delivery

## Objective
Deliver the user-facing experience for idea intake and structure refinement, enabling authors to see the seven-agent loop in action, review critiques, perform manual edits, and approve the final outline that feeds later stages.

## Scope & Context
- Builds upon Phase 6 frontend scaffolding and Phase 5 structure generation backend.
- Focuses on two key UX moments: capturing the initial 100-word idea and visualising iterative structure refinement with full transparency.
- Synchronises with the category-based library, updating project cards to reflect idea submission and structure completion status.
- Must maintain alignment with the overall IA: the structure becomes the root artifact for titles, research, emotional layers, and writing.

## Key Deliverables
- Idea intake screen with validation, tone guidance, and preview of downstream stages.
- Structure Lab interface featuring timeline of agent rounds (S1 → S7), diff viewer for each critique/implementation pair, and inline manual editing with schema validation.
- Control panel allowing users to accept current iteration, request rerun, edit before proceeding, and tweak per-agent LLM settings (model, temperature, JSON mode) for subsequent stages.
- Automatic status badges pushed back to the library dashboard (Idea logged, Structure in progress/completed).
- Onboarding tips/tooltips highlighting how structure quality impacts Deep Research and writing phases.

## Milestones & Tasks
1. Integrate orchestrator events to stream agent reasoning and results into the UI.
2. Implement diff rendering leveraging shared components from Phase 6.
3. Hook manual edits back to backend validation, ensuring updates re-trigger necessary critiques if rules change.
4. Update library state in real time so category view shows latest progress and timestamps.
5. Provide export/print options for the approved structure for offline review.
6. Conduct usability test (internal) to ensure the flow is understandable before Phase 8 begins.

## Dependencies
- Phase 5 structure data and APIs.
- Phase 6 frontend infrastructure.
- Schema definitions (Phase 2) for validation messages.

## Risks & Mitigations
- **Risk**: Users overwhelmed by agent activity.
  - *Mitigation*: Provide summary cards and ability to collapse agent details.
- **Risk**: Manual edits create inconsistencies.
  - *Mitigation*: Highlight validation errors immediately and require fixes before advancing.

## Exit Criteria
- Users can complete idea intake and structure approval in a single session using mock or real LLMs.
- All agent iterations and diffs accessible through UI history.
- Library dashboard displays updated stage for the project immediately after approval.
- Final structure persists and unlocks Phase 8 Title Ideation flow.

## Handoffs & Next Steps
- Pass finalized structure and metadata to Title Ideation (Phase 8) and Research Prompt Pipeline (Phase 9).
- Gather feedback to inform improvements in critique explanations for future phases.
