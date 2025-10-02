# Phase 5 – Structure Generation Flow

The orchestrator now executes a multi-agent loop whenever the `STRUCTURE` stage runs.

1. **Proposal Agent**: calls the provider with `STRUCTURE_PROPOSAL_PROMPT` to produce an
   initial `BookStructure` JSON document.
2. **Critique Agent**: analyses the current structure and emits improvement notes.
3. **Improvement Agent**: updates the structure JSON according to critique feedback.
   Steps 2–3 repeat three times to simulate the seven-agent workflow (proposal + three
   critique/improvement cycles + final summary).
4. **Summary Agent**: generates a narrative summary of the final structure for logging
   and UI preview.

The loop is implemented in `services/orchestrator/app/structure/engine.py`. It enforces
schema validation via `BookStructure.model_validate` and returns:

- `BookStructure` object (also attached to `StageRunResult.structured_output`).
- Final summary text used in activity feeds.
- List of critiques (saved for future UI diffs and audit trails).

Stage-level provider overrides are honoured: the frontend can supply distinct models,
temperatures, or token limits for the structure agents while other stages continue to
use global defaults.
