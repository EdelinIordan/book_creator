# Phase 4 – Workflow Orchestrator MVP

## Objective
Stand up the deterministic state machine that manages the end-to-end non-fiction book workflow, coordinating agents across structure building, title selection, research, emotional layering, and writing while persisting progress.

## Scope & Context
- Uses Phase 1 environment, Phase 2 schemas, and Phase 3 provider adapters to implement orchestrated runs.
- Focuses on infrastructure: state transitions, retries, persistence, and health monitoring. Feature-specific logic comes in later phases.
- Ensures every project can pause/resume, roll back to previous stages, and record audit logs for each agent exchange.

## Key Deliverables
- Prefect 2 orchestration framework setup with core project scaffolding.
- State machine definition mapping the seven major stages from the product plan (Idea Intake, Structure Loop S1–S7, Title Selection T1, Research Prompt Triad R1–R3, Research Fact Mapping I0/M1–M3, Emotional Layer E1–E3, Proper Writing stack G1–G3 + W1–W7) and their internal agent loops.
- REST endpoint (`POST /orchestrator/run`) that executes stage sequences using configured providers (OpenAI, Gemini, or mock) with optional per-stage overrides for model/temperature/token limits.
- Configuration hooks wiring environment-based provider selection, including optional overrides per request.
- Persistence layer (placeholder) ready for future expansion to store run logs and progress snapshots.
- API endpoints (or events) to trigger runs, advance stages, stream status updates, and notify category dashboards of progress changes.

## Milestones & Tasks
1. Implement base Prefect workflow runner supporting start/pause/resume/cancel operations.
2. Configure Prefect storage and blocks suitable for local-first deployments.
3. Encode stage transitions with guard conditions (e.g., structure must be finalized before titles run).
4. Integrate Redis queues for task dispatch to agent workers and capture heartbeat checks (placeholder in Phase 4).
5. Emit normalized progress events (stage transitions, percentage completion) consumed by the library UI (future).
6. Instrument logging/tracing hooks for later observability work.

## Dependencies
- Phase 1 environment configured with Prefect binaries and agent services.
- Schemas (Phase 2) and provider interfaces (Phase 3) for validating tasks and executing LLM calls.

## Risks & Mitigations
- **Risk**: Workflow complexity leads to brittle state handling.
  - *Mitigation*: Represent stages declaratively with configuration files and add extensive unit/integration tests.
- **Risk**: Long-running tasks stall the orchestrator.
  - *Mitigation*: Use timeouts and compensating actions; expose manual override controls.

## Exit Criteria
- Sample “hello world” workflow runs through all stages using mock LLMs, persisting outputs per stage.
- Orchestrator exposes `/health`, `/stages/defaults`, and `/orchestrator/run` endpoints.
- Documentation explains how to add new stages or modify transitions, and how to supply OpenAI/Gemini credentials.

## Handoffs & Next Steps
- Enable Phase 5+ teams to plug their stage-specific logic into the orchestrator skeleton.
- Provide event schemas to frontend team for streaming agent updates during Phase 7 and beyond.
