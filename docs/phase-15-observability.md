# Phase 15 – Observability & Ops

## Objective
Implement monitoring, logging, and operational tooling that provide insight into agent performance, cost, latency, and failure patterns across the full book creation pipeline.

## Scope & Context
- Builds on instrumentation hooks added during earlier phases, turning them into actionable dashboards and alerts.
- Ensures the local Docker stack still offers transparency for developers and advanced users monitoring long-running projects.
- Supports debugging complex multi-agent interactions (structure critiques, fact mapping, writing cycles).

## Key Deliverables
- Centralised logging framework with structured context (project ID, stage, agent role, provider, cost, latency).
- Metrics collection using Prometheus/OpenTelemetry, exposing dashboards via Grafana or lightweight UI, including category-level aggregates (books per stage, average completion time per category).
- Alerting rules for critical failures (workflow stalls, provider errors, schema violations).
- Cost tracking reports per project and per stage, feeding into Phase 16 controls.

## Milestones & Tasks
1. Configure logging stack within Docker Compose, ensuring logs persist locally and are queryable.
2. Instrument orchestrator, agent workers, and API endpoints with tracing spans and metrics.
3. Create dashboards highlighting workflow throughput, agent success rates, average iteration counts, cost per book, and library analytics (projects per category/stage over time).
4. Implement notification hooks (email/desktop) for long-running tasks or failures (optional for v1).
5. Document operational runbooks for diagnosing issues, correlating logs, and restarting stuck workflows.

## Dependencies
- Provider instrumentation (Phase 3) and orchestrator logging capabilities (Phase 4).
- Functional stages (Phases 5–13) to provide real data for dashboards.
- Testing groundwork (Phase 14) ensuring instrumentation doesn’t break logic.

## Risks & Mitigations
- **Risk**: Observability stack adds significant overhead.
  - *Mitigation*: Allow users to disable heavy components or sample metrics in low-resource environments.
- **Risk**: Local-only deployment complicates alerting.
  - *Mitigation*: Provide optional integrations (webhooks) that users can configure per their environment.

## Exit Criteria
- Developers can inspect logs and metrics for any project, identifying bottlenecks or failures quickly.
- Dashboards reflect key success metrics defined in Phase 0 (completion rate, cost per book, etc.).
- Runbooks exist for common operational scenarios.

## Implementation Summary (v0.1)
- Introduced `libs/python/book_creator_observability` to centralise JSON logging, Prometheus middleware, and worker heartbeat helpers.
- API, orchestrator, doc parser, and agent worker services now call `setup_logging` and expose `/metrics`; orchestrator stages emit duration and provider token metrics.
- Docker Compose bundles Prometheus (`infra/observability/prometheus.yml`) and Grafana (`infra/observability/grafana/*`) with a starter dashboard at <http://localhost:3110>.
- Agent workers publish `book_creator_worker_heartbeat_timestamp` on port `9500`, enabling scrape-based liveness checks.
- Operational instructions live in `docs/runbooks/observability.md`.
- Containers set `BOOK_CREATOR_CAPTURE_WARNINGS=1` so Python warnings (e.g., Pydantic deprecations) land in structured logs when running locally.

## Operational Notes
- Start the monitoring stack with `docker compose up prometheus grafana` once core services are running.
- Prometheus scrapes every 15 seconds; tweak the interval or add alert rules for sustained latency or missing heartbeats.
- Extend Grafana by dropping additional dashboard JSON into `infra/observability/grafana/dashboards`.
- Capture logs with `docker compose logs -f <service>`; each record includes `service`, `stage`, `project_id`, and (when available) `run_id` to simplify correlation.

## Handoffs & Next Steps
- Feed cost and latency insights into Phase 16 (Performance & Cost Controls).
- Use observability findings to prioritise bug fixes before pre-launch validation (Phase 19).
