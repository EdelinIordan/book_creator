# Documentation Index

Use this guide as an entry point to the project’s documentation. Folder paths are relative to the repository root.

## Experience & Product Guides
- `docs/user-walkthrough.md` – end-to-end tour of the Book Creator workflow with stage-specific tips.
- `docs/user-app-description-and-agents-roster.md` – detailed description of agents, handoffs, and personas that underpin each stage.
- `docs/frontend-architecture.md` – UI composition, routing strategy, and shared component notes.
- `docs/frontend-provider-settings.md` – guidance for managing provider overrides in the Agents & API views.
- `docs/design/design-principles.md` – visual language, theming tokens, and interaction standards for the app.

## Contributor Setup & Tooling
- `docs/development-setup.md` – local environment requirements, Make targets, and service map.
- `docs/provider-usage.md` – installing the shared providers package and wiring SDK overrides.
- `docs/chatgpt5-gemini25-integration.md` – deep-dive on dual-provider orchestration.
- `docs/architecture/phase-5-structure-flow.md` – outlines how structure data flows from orchestrator to UI.

## API, Schema & Data References
- `docs/architecture/phase-2-erd.md` – database entity relationship diagrams.
- `docs/architecture/phase-2-sample-payloads.md` – canonical API payloads for each major stage.
- `libs/python` (package `book_creator_schemas`) – source of all shared Pydantic models and enums.
- `services/` – background workers, orchestrator flows, and adapters referenced by the docs above.

## Operations & Runbooks
- `docs/runbooks/` – service-specific playbooks for recovery, test data refresh, and incident response.
- `docs/provider-usage.md` → *Observability Hooks* – tie-ins to Phase 15 dashboards and metrics.

## Phase Roadmaps
- `docs/phase-0-foundations.md` through `docs/phase-20-launch-iteration.md` – milestone-by-milestone objectives, exit criteria, and handoffs spanning the full programme. Each document links to the preceding and following phases.

When adding new docs, update this index so future contributors know where to look first.
