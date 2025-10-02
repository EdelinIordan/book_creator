"""Placeholder agent worker that simulates queue consumption during Phase 1."""

import logging
import time

from book_creator_observability import (
    record_worker_heartbeat,
    setup_logging,
    start_metrics_server,
)

SERVICE_NAME = "agent_workers"
METRICS_PORT = 9500

setup_logging(SERVICE_NAME)
logger = logging.getLogger(__name__)


def main() -> None:
    start_metrics_server(METRICS_PORT)
    logger.info("agent worker booted", extra={"metrics_port": METRICS_PORT})
    while True:
        record_worker_heartbeat(SERVICE_NAME)
        logger.info("agent worker idle heartbeat")
        time.sleep(60)


if __name__ == "__main__":
    main()
