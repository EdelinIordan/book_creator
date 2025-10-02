# Observability Runbook

This guide explains how to monitor the Book Creator stack after Phase 15.

## Structured Logging
- All services emit JSON logs with contextual fields (`service`, `stage`, `project_id`, `run_id`).
- View live logs with `docker compose logs -f api orchestrator doc_parser agent_workers`.
- Filter for a specific project using `jq`, e.g.:
  ```bash
  docker compose logs orchestrator | jq 'select(.project_id=="<UUID>")'
  ```
- Error events include stack traces and keep the contextual fields for faster correlation.
- `BOOK_CREATOR_CAPTURE_WARNINGS=1` (set in docker-compose) routes Python warnings into the structured logs so regressions are visible alongside normal events.

## Metrics & Alerts
- Prometheus runs inside Docker at <http://localhost:9090> using `infra/observability/prometheus.yml`.
- Default scrape targets:
  - API: `api:8000/metrics`
  - Orchestrator: `orchestrator:9100/metrics`
  - Doc parser: `doc_parser:9200/metrics`
  - Agent workers: `agent_workers:9500/metrics`
- Core metrics:
  - `book_creator_http_requests_total`: HTTP throughput by service.
  - `book_creator_http_request_duration_seconds`: latency histograms per route.
  - `book_creator_stage_duration_seconds`: end-to-end stage execution time.
  - `book_creator_llm_tokens_total` / `book_creator_llm_cost_usd_total`: LLM usage per stage.
  - `book_creator_worker_heartbeat_timestamp`: latest worker heartbeat.
- Add alerting rules in Prometheus when you are ready for paging (e.g. high p95 stage duration, missing worker heartbeat).

## Dashboards
- Grafana runs at <http://localhost:3110> (admin/admin).
- The `Book Creator Overview` dashboard tracks stage latency p95 and request throughput; extend it as needed for cost and error rates.
- Project-level spend is persisted in `projects.total_cost_cents`; combine with Prometheus counters for per-stage breakdowns when investigating runaway budgets.
- Attach Prometheus as the `prometheus` data source if it is not auto-detected.

## Troubleshooting
- **No metrics**: confirm containers are on the `booknet` network and ports 8000/9100/9200/9500 are open. Check Prometheus targets page for scrape errors.
- **Grafana empty**: verify dashboard provisioning volume mounts under `infra/observability/grafana`.
- **Logs missing context**: ensure services can import `book_creator_observability` and call `setup_logging()` before first log emission.
- **Worker heartbeat stale**: inspect the agent worker logs; the metric should update every 60 seconds. Restart `agent_workers` if timestamps freeze.

## Daily Checklist
1. Check Grafana dashboard for latency or throughput anomalies.
2. Review Prometheus alerts or manual queries for rising LLM cost metrics.
3. Scan orchestrator logs filtered by `stage` to confirm no repeated failures.
4. Verify agent worker heartbeat metric is fresh (> 60 seconds).

Keep this runbook with the Phase 15 deliverables and update it when you add alerting rules or additional dashboards.
