# Phase 8 – Title Ideation Flow

## Backend
- `services/orchestrator/app/title/engine.py` orchestrates proposal → critique → rewrite steps.
- Uses provider abstraction to return a `TitleBatch` (Pydantic schema added in Phase 8) and critique notes.
- Orchestrator attaches structured results to `StageRunResult.structured_output` for downstream phases.
- Stage-level provider overrides (model/temperature) are honored, falling back to run-level defaults.

## Frontend
- New route `/projects/[id]/titles` provides:
  - Title cards with rationales and shortlist/selection controls.
  - Regenerate button (currently shuffles mock data until live API hook is added).
  - Final selection panel and stage LLM override controls mirroring backend schema.
- Mock data lives in `src/lib/mock-titles.ts`; once persistence exists, replace with real API calls.

## Next Steps
- Implement API endpoints to fetch/store title batches, shortlist, and final selection.
- Track regeneration counts and estimated provider cost per batch.
- Display critique text in UI (e.g., under a "Creative Director Notes" section).
- Trigger library status updates after confirmation to unblock Phase 9 research planning.
