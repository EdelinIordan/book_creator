# Phase 1 – Environment & Tooling

## Objective
Set up the local-first development environment and shared tooling that will power the multi-agent non-fiction book workflow described in Phase 0, ensuring every contributor can run the entire Docker stack (frontend, API, orchestrator, workers, Postgres, Redis, vector store, object storage) with minimal effort.

## Scope & Context
- Builds directly on the product vision: agents iteratively craft structure, research prompts, emotional layers, and final drafts using Gemini 2.5 Pro or ChatGPT 5.
- Prepares the infrastructure needed for later phases to implement orchestrated stages, DOCX ingestion, and UI wizard flows.
- Focused on developer ergonomics, not on user-facing features yet.

## Key Deliverables
- Docker Compose skeleton with service stubs for frontend, API gateway, workflow orchestrator, agent workers, Postgres, Redis, vector store (pgvector/Qdrant), and MinIO (or equivalent) for DOCX uploads.
- Standardised development scripts (`make` or task runner) for bootstrapping, testing, and linting.
- Pre-commit hook configuration and baseline lint/format/test commands wired into CI scaffolding.
- Sample `.env.example` reflecting provider credentials (Gemini/ChatGPT) and storage secrets without exposing real keys.
- Seed data mechanism or fixtures supporting the category-based library dashboard (sample categories, staged projects) for later UI development.

## Milestones & Tasks
1. Author base Dockerfiles for frontend (Node), backend (Python), and worker images.
2. Compose orchestrator/worker network, mount volumes for Postgres and MinIO, and document resource expectations.
3. Install Prefect 2 in the orchestrator service and expose a placeholder flow endpoint for health validation.
4. Configure linting (Ruff/Black, ESLint/Prettier) and testing harnesses (Pytest/Vitest) with placeholder tests.
5. Implement pre-commit hooks and GitHub Actions workflows (lint/test/build placeholders).
6. Provision sample database migrations or fixtures populating example categories and project status snapshots for the future library view.
7. Draft developer onboarding guide referencing Phase 0 policies (privacy, provider usage, coding standards).

## Dependencies
- Phase 0 documentation for coding standards, provider strategy, and repository layout.
- Prefect 2 selected as the orchestrator framework; ensure container images include required dependencies and CLI tooling.

## Risks & Mitigations
- **Risk**: Docker resource usage overwhelms local machines when all services run in tandem.
  - *Mitigation*: Provide profiles to start subsets (e.g., skip workers by default) and document minimum specs.
- **Risk**: Provider SDKs or CLIs needed for later phases complicate container builds.
  - *Mitigation*: Add placeholder packages with clear TODOs and version pins to avoid future drift.

## Exit Criteria
- Running `docker compose up` starts all placeholder services and surfaces health endpoints/logs confirming readiness, including the Prefect placeholder flow endpoint.
- Lint/test commands succeed locally and in CI using placeholder code.
- Sample data for categories/projects loads successfully, enabling Phase 6 to visualise the library dashboard.
- Onboarding guide allows a new developer to set up environment within one hour.

## Handoffs & Next Steps
- Provide environment scripts and documentation to Phase 2 owners so they can generate domain models within the established structure.
- Log any unresolved decisions (e.g., final orchestrator framework) in project tracker before moving to Phase 2.
