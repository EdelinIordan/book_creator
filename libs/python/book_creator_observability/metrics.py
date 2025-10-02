"""Prometheus metrics helpers and middleware."""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Optional, Tuple
import warnings

from fastapi import FastAPI, Response
try:  # pragma: no cover - fallback for environments without prometheus_client
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
        start_http_server,
    )
    _PROMETHEUS_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - executed in minimal test envs
    _PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class _NoOpMetric:
        def labels(self, *args, **kwargs):  # type: ignore[explicit-any]
            return self

        def observe(self, *args, **kwargs):  # type: ignore[explicit-any]
            return None

        def inc(self, *args, **kwargs):  # type: ignore[explicit-any]
            return None

        def set_to_current_time(self):
            return None

    def _no_op_metric_factory(*args, **kwargs):  # type: ignore[explicit-any]
        return _NoOpMetric()

    Counter = Histogram = Gauge = _no_op_metric_factory  # type: ignore[assignment]

    def generate_latest() -> bytes:
        return b""

    def start_http_server(*args, **kwargs):  # type: ignore[override]
        return None

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from book_creator_providers.base import ProviderResponse


_HTTP_REQUEST_COUNT = Counter(
    "book_creator_http_requests_total",
    "Total HTTP requests processed by service",
    labelnames=("service", "method", "route", "status"),
)

_HTTP_REQUEST_LATENCY = Histogram(
    "book_creator_http_request_duration_seconds",
    "Latency of HTTP requests",
    labelnames=("service", "method", "route"),
)

_STAGE_DURATION = Histogram(
    "book_creator_stage_duration_seconds",
    "Duration of book creation stages",
    labelnames=("service", "stage"),
)

_STAGE_COUNTER = Counter(
    "book_creator_stage_runs_total",
    "Count of stage executions by outcome",
    labelnames=("service", "stage", "status"),
)

_LLM_TOKENS = Counter(
    "book_creator_llm_tokens_total",
    "Token usage by provider and stage",
    labelnames=("service", "stage", "provider", "token_type"),
)

_LLM_COST = Counter(
    "book_creator_llm_cost_usd_total",
    "Aggregated LLM cost in USD",
    labelnames=("service", "stage", "provider"),
)

_LLM_LATENCY = Histogram(
    "book_creator_llm_latency_seconds",
    "Latency of LLM provider calls",
    labelnames=("service", "stage", "provider"),
)

_WORKER_HEARTBEAT = Gauge(
    "book_creator_worker_heartbeat_timestamp",
    "Unix timestamp for the latest worker heartbeat",
    labelnames=("service",),
)

_STARTUP_FLAGS: set[Tuple[str, int]] = set()


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Collect request metrics for FastAPI services."""

    def __init__(self, app: FastAPI, service_name: str) -> None:
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start = perf_counter()
        response = await call_next(request)
        elapsed = perf_counter() - start

        route_template = request.url.path
        route = request.scope.get("route")
        if route and getattr(route, "path", None):
            route_template = route.path  # type: ignore[assignment]

        method = request.method
        status = getattr(response, "status_code", 500)

        _HTTP_REQUEST_COUNT.labels(self.service_name, method, route_template, str(status)).inc()
        _HTTP_REQUEST_LATENCY.labels(self.service_name, method, route_template).observe(elapsed)
        return response


def setup_fastapi_metrics(app: FastAPI, service_name: str, endpoint: str = "/metrics") -> None:
    """Register Prometheus middleware and metrics endpoint for a FastAPI app."""

    if getattr(app.state, "metrics_configured", False):
        return

    app.add_middleware(PrometheusMiddleware, service_name=service_name)

    @app.get(endpoint, include_in_schema=False)
    async def _metrics_endpoint() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app.state.metrics_configured = True


def start_metrics_server(port: int, addr: str = "0.0.0.0") -> None:
    """Expose Prometheus metrics on a standalone HTTP server."""

    key = (addr, port)
    if key in _STARTUP_FLAGS:
        return
    start_http_server(port, addr=addr)
    _STARTUP_FLAGS.add(key)


def observe_stage_duration(
    stage: str,
    duration_seconds: float,
    *,
    service_name: str,
    status: str = "success",
) -> None:
    """Record metrics for stage execution duration and outcome."""

    _STAGE_DURATION.labels(service_name, stage).observe(max(duration_seconds, 0.0))
    _STAGE_COUNTER.labels(service_name, stage, status).inc()


def observe_provider_response(
    *,
    stage: str,
    provider: str,
    service_name: str,
    response: Optional["ProviderResponse"],
) -> None:
    """Capture token usage, latency, and cost from provider responses."""

    if response is None:
        return

    prompt_tokens = getattr(response, "prompt_tokens", None)
    if isinstance(prompt_tokens, (int, float)) and prompt_tokens >= 0:
        _LLM_TOKENS.labels(service_name, stage, provider, "prompt").inc(prompt_tokens)

    completion_tokens = getattr(response, "completion_tokens", None)
    if isinstance(completion_tokens, (int, float)) and completion_tokens >= 0:
        _LLM_TOKENS.labels(service_name, stage, provider, "completion").inc(completion_tokens)

    latency_ms = getattr(response, "latency_ms", None)
    if isinstance(latency_ms, (int, float)) and latency_ms >= 0:
        _LLM_LATENCY.labels(service_name, stage, provider).observe(latency_ms / 1000)

    cost_usd = getattr(response, "cost_usd", None)
    if isinstance(cost_usd, (int, float)) and cost_usd >= 0:
        _LLM_COST.labels(service_name, stage, provider).inc(cost_usd)


def record_worker_heartbeat(service_name: str) -> None:
    """Update the heartbeat gauge for long-running worker processes."""

    _WORKER_HEARTBEAT.labels(service_name).set_to_current_time()
