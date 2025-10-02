# Phase 2 – Domain Modeling & Schemas

## Objective
Define the shared data contracts that represent every artifact in the seven-stage book creation pipeline so subsequent phases can persist and exchange information without ambiguity.

## Scope & Context
- Translates Phase 0’s vision and Phase 1’s environment into concrete Python (Pydantic) and TypeScript types.
- Covers models for idea briefs, structured outlines, agent critiques, research prompts, research facts with citations, emotional layer entries, creative director guidelines, multi-pass drafts, and project library metadata (categories, stage statuses, progress metrics).
- Provides serialization formats for API/worker communication and database storage (Postgres with pgvector).

## Key Deliverables
- Pydantic models and validation schemas in `libs/python` for backend/orchestrator use (`book_creator_schemas`).
- TypeScript interfaces and Zod schemas in `libs/ts` for frontend/API client consistency.
- Entity-relationship diagram aligning with Postgres schema, including vector index strategy for research facts.
- Project library schema covering categories, stage enums, progress snapshots, and analytics counters.
- OpenAPI/JSON Schema definitions documenting API payloads.

## Milestones & Tasks
1. Catalogue every agent exchange across phases (structure refinement, research prompt iteration, emotional layering, writing loop) and list required fields.
2. Create shared enums/constants (e.g., stage identifiers, agent roles, critique types) to avoid string literals.
3. Implement validation logic for hierarchical book structure (chapters → subchapters → facts/stories/guidelines).
4. Define project status progression model feeding the category dashboard (e.g., Idea, Structure, Research, Emotional, Writing, Completed) with timestamps for analytics.
5. Design citation model linking extracted facts to DOCX metadata (source title, author, publication date, page/section).
6. Document JSON schema versions and migration strategy for future prompt tweaks.
7. Establish Alembic scaffolding to manage future database migrations.

## Dependencies
- Phase 0 success metrics, ensuring models capture fields needed for coverage and quality scores.
- Phase 1 repository layout and tooling for code placement and linting.

## Risks & Mitigations
- **Risk**: Under-specified schemas cause downstream agents to produce unstructured text.
  - *Mitigation*: Include strict required fields and automated schema validation tests.
- **Risk**: Schema changes later require costly migrations.
  - *Mitigation*: Introduce versioned schema namespace and migration scripts from the start.

## Exit Criteria
- Schemas reviewed with orchestrator and frontend stakeholders for completeness.
- Example serialized payloads available for each workflow stage and for category/stage summary endpoints.
- ERD approved; migrations scaffolded but not yet applied (reserved for Phase 4 when persistence is wired).

## Handoffs & Next Steps
- Provide schema documentation (`libs/python/book_creator_schemas`, `libs/ts/src`) to Phase 3 (provider adapter authors) and Phase 4 (orchestrator) so they can enforce structured outputs and persistence.
- Point frontend contributors to the sample payloads (`docs/architecture/phase-2-sample-payloads.md`) when wiring mock data.
- Update onboarding docs to reference schema package usage.
