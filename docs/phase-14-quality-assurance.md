# Phase 14 – Cross-Cutting Quality Assurance

## Objective
Establish automated and manual testing strategies that validate every component of the non-fiction book workflow, from schema validation to end-to-end agent orchestration, ensuring reliable output before launch.

## Scope & Context
- Enhances confidence in the multi-agent pipeline after core features (structure, research, emotional layer, writing) are implemented.
- Focuses on testing, validation, and safety checks rather than new user-facing functionality.
- Integrates with CI/CD and local tooling defined in Phase 1.

## Key Deliverables
- Unit test suites for schemas, provider adapters, and orchestrator transitions.
- Integration tests simulating multi-stage workflows with mock LLM responses.
- UI tests (Playwright) covering critical flows: idea intake, structure approval, title selection, research upload, fact mapping, emotional review, writing acceptance, and library dashboard filtering/status updates.
- Automated hallucination and citation consistency checks leveraging heuristics or lightweight models.

### Current Coverage Snapshot
- Added regression tests for the writing engine, validating both resolved and outstanding feedback paths with mocked agent responses.
- Extended orchestrator flow tests to include the WRITING stage, ensuring structured outputs and critique metadata are returned.
- Shared prompt utilities (`tests/utils/prompts.py`) simplify parsing embedded JSON in prompt templates for future QA scenarios.

## Milestones & Tasks
1. Expand Pytest suite to cover orchestrator state transitions, ensuring retries and failure modes behave as expected.
2. Create synthetic datasets to simulate research facts and emotional stories, verifying deduplication logic.
3. Implement Playwright scenarios for the end-to-end wizard with mocked API responses, including category creation and progress tracking across multiple projects.
4. Add regression tests for cost/latency logging hooks to prevent telemetry gaps.
5. Integrate coverage reporting and quality gates into CI workflows.

## Dependencies
- Functional features from Phases 5–13.
- Mock provider outputs from Phase 3.
- Docker environment (Phase 1) capable of running tests headlessly.

## Risks & Mitigations
- **Risk**: Test suite becomes too slow for local use.
  - *Mitigation*: Support parallel execution and targeted test commands.
- **Risk**: Mock outputs diverge from real provider behavior.
  - *Mitigation*: Periodically capture real responses for regression comparison and update mocks accordingly.

## Exit Criteria
- CI pipeline runs full test suite with acceptable duration and high coverage.
- Critical user journeys validated by automated tests and smoke-tested manually, including dashboard category summaries.
- Known gaps documented with mitigation plan (e.g., manual regression checklist).

## Handoffs & Next Steps
- Provide QA results to Phase 15 (Observability) and Phase 19 (Pre-Launch Validation) teams to inform readiness assessments.
- Use findings to refine prompts or data models as needed before final polishing.
