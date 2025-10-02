# Phase 16 – Performance & Cost Controls

## Objective
Optimize system performance and manage LLM expenditure by introducing context management, caching, batching, and user-facing budget controls across the multi-agent workflow.

## Scope & Context
- Relies on observability data (Phase 15) to identify bottlenecks in structure loops, research parsing, emotional layering, and writing cycles.
- Implements adaptive strategies so the seven-stage pipeline remains responsive and affordable when running locally with external LLM APIs.
- Adds UI feedback on estimated costs and progress to keep users informed.

## Key Deliverables
- Context window trimming utilities that summarise history before sending to agents with limited token budgets.
- Result caching for repeated agent prompts (e.g., regenerating structure critiques with same inputs).
- Batched operations where possible, such as evaluating multiple subchapters in parallel within resource constraints.
- Budget management UI allowing users to set spending limits, see per-stage estimates, receive warnings when thresholds near, and compare costs across categories.

## Milestones & Tasks
1. Analyze metrics from Phase 15 to prioritize highest-cost/latency agents.
2. Implement caching layer keyed by stage, inputs, and provider to reuse prior outputs safely.
3. Add summarization models (smaller LLM/local) to compress context while preserving essential facts and instructions.
4. Update orchestrator to respect budget ceilings, pausing stages when limits reached and notifying users.
5. Surface cost and performance indicators in frontend dashboards and the library view (category-level summaries).

## Dependencies
- Observability stack (Phase 15).
- Provider abstraction (Phase 3) for implementing caching and summarization wrappers.
- Orchestrator (Phase 4) to enforce budget gating.

## Risks & Mitigations
- **Risk**: Aggressive summarization degrades output quality.
  - *Mitigation*: Allow per-stage tuning, testing impact rigorously before enabling by default.
- **Risk**: Caching returns outdated results after user edits.
  - *Mitigation*: Include cache invalidation hooks triggered by manual changes or schema version bumps.

## Implementation Notes
- Provider adapters (OpenAI GPT‑5 and Gemini 2.5) now estimate request cost using the published token pricing tables. Each stage response includes `cost_usd`, which the API persists per project and surfaces in Prometheus metrics.
- The API records cumulative spend in `projects.total_cost_cents` and enforces a soft ceiling stored in `projects.spend_limit_cents`. Stage orchestration halts with a 402 error once the limit is reached, ensuring budgets are respected without silently incurring more usage.
- Provider responses are cached via a Redis-backed (with in-process fallback) stage cache. Cache keys incorporate provider, model, stage, prompt, and sampling parameters, reducing duplicate LLM calls for identical inputs. Requests are trimmed to a configurable token budget before execution to avoid runaway contexts.
- The dashboard now displays live spend per project, remaining budget, and warning states (`warning` at ≥90 % and `exceeded` when the limit is hit). Users can set or clear budgets inline; the UI routes through the new `PATCH /projects/{id}/budget` endpoint.

## Operating the New Controls
- **Setting budgets**: Open the dashboard card for a project and use *Set budget* → enter a USD amount → *Save*. Leave the field blank to remove the ceiling. The card updates immediately with the revised summary returned by the API.
- **Monitoring spend**: Spend and remaining budget are rendered directly on each card. When usage reaches 90 % of the limit the badge switches to *Budget nearly used*; at or beyond 100 % the badge turns red and further stage runs are blocked until the ceiling is raised.
- **Observability**: Cost telemetry continues to aggregate under `book_creator_llm_cost_usd_total` and per-stage averages in `/stats/agent-stage`. Project-level totals can be queried from the `projects` table for bespoke reporting.

## Exit Criteria
- Performance improvements measured (e.g., reduced latency or cost) documented with before/after metrics.
- Budget controls functioning with clear user messaging and overrides when necessary.
- No regression in output quality confirmed via targeted QA tests.

## Handoffs & Next Steps
- Provide optimization patterns to future enhancement phases or plugin development.
- Inform Phase 19 pre-launch planning with updated cost expectations and recommended default limits.
