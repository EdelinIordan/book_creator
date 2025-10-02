# Phase 3 – Provider Abstraction Layer

## Objective
Implement a unified interface for interacting with Google Gemini 2.5 Pro and OpenAI ChatGPT 5 so every agent in the book-writing workflow can swap providers without changing business logic.

## Scope & Context
- Builds on schemas from Phase 2 to define request/response contracts for LLM calls.
- Provides adapters and utilities that will be consumed by orchestrator tasks, agent workers, and test harnesses across structure generation, research prompt creation, emotional layering, and writing.
- Includes offline mock transport to enable development without live API usage.

## Key Deliverables
- Python provider package (`book_creator_providers`) exposing consistent interfaces for Gemini, ChatGPT, and mock responses.
- Configuration layer supporting per-stage parameters (temperature, max tokens, safety settings) and fallback logic.
- Cost/latency logging hook integrated with observability plans from Phase 15.
- Mock LLM module returning deterministic sample outputs for CI and local tests.

## Milestones & Tasks
1. Catalogue capabilities required per agent role (e.g., long context for structure critique, precise JSON for fact mapping).
2. Implement adapters for Gemini and ChatGPT with environment-driven credential loading and retry policies.
3. Add response validation to ensure outputs conform to Phase 2 schemas; implement auto-repair strategies (e.g., re-prompting for malformed JSON).
4. Expose provider selection API so orchestrator can choose provider per stage or per project.
5. Document usage patterns in developer guide, including examples for invoking mock vs. real providers (`docs/provider-usage.md`).

## Dependencies
- Phase 1 environment (Docker images must include provider SDKs and dependencies; install via `pip install -e libs/python[providers]`).
- Phase 2 schemas for typing and validation.

## Risks & Mitigations
- **Risk**: Provider APIs evolve, breaking adapters.
  - *Mitigation*: Encapsulate external SDK usage and maintain integration tests with mock responses mirroring real payloads.
- **Risk**: Cost overruns if retries are poorly managed.
  - *Mitigation*: Implement per-call and per-stage budget caps with graceful degradation.

## Exit Criteria
- Unit tests demonstrating provider swap with identical orchestrator code.
- Mock transport wired into CI, ensuring no real API calls on pull requests.
- Documentation describing configuration steps for both providers, including rate limit considerations.

## Handoffs & Next Steps
- Deliver provider interfaces to Phase 4 for orchestrator integration and to later feature phases for agent implementation.
- Share cost telemetry hooks with Phase 16 (Performance & Cost Controls) owners.
