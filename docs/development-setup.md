# Development Setup Guide

This guide helps contributors bootstrap the local-first book creator stack during Phase 1.

## Prerequisites
- Docker Desktop 4.24+ with Compose v2
- Make (optional but recommended)
- Python 3.11+
- Node.js 20+

## First-Time Setup
1. Clone the repository and change into the project directory.
2. Copy the environment template:
   ```bash
   make setup
   ```
3. Install dependencies for the API, shared schemas, and frontend (optional for container-only development):
   ```bash
   make install
   ```
   If your shell does not expose the `pip` command, run `python3 -m pip install -r apps/api/requirements-dev.txt` instead.
4. Start the stack:
   ```bash
   make docker-up
   ```
5. Visit `http://localhost:3100` to confirm the Library Dashboard loads. The FastAPI gateway responds on `http://localhost:8000/health`.
6. Trigger the orchestrator by POSTing to `http://localhost:9100/orchestrator/run` (see `docs/provider-usage.md` for sample payloads).

## Services in the Phase 1 Compose Stack
| Service | Port | Purpose |
| --- | --- | --- |
| frontend | 3100 | Next.js scaffold with placeholder library view |
| api | 8000 | FastAPI gateway health endpoint |
| orchestrator | 9100 | Prefect-based workflow orchestrator |
| agent_workers | n/a | Simulated agent worker heartbeat |
 | doc_parser | 9300 | Placeholder DOCX parser API |
 | postgres | 5433 | Stores categories, projects, and future workflow data |
 | redis | 6380 | Queue/cache placeholder |
 | qdrant | 6333 | Vector store placeholder |
 | minio | 9000/9001 | Object storage placeholder |

> Uploaded research files are stored locally under `storage/research_uploads/`. Clean this directory if you want to reset uploaded artefacts between runs.

## Seed Data
When the stack boots, PostgreSQL executes SQL files under `data/seeds/postgres/`. The seed scripts create:
- Default categories with color assignments (History, Psychology, Popular Science, Health).
- Sample projects across different stages so the library dashboard has data to visualise during Phase 6.

## Linting & Tests
- Run `make lint` (or `npm run lint` inside `apps/frontend`) for TypeScript/React lint checks.
- Execute Python unit suites with `python3 -m pytest tests/unit` — this now covers schemas, provider adapters, orchestrator flows, and the Phase 13 writing engine QA specs.
- Focused runs are supported, e.g. `python3 -m pytest tests/unit/test_writing_engine.py -vv` to debug the new feedback resolution scenarios.
- Pre-commit hooks can be installed with `pre-commit install` once the tool is available locally.

## Tear Down
- Stop services with `make docker-down`.
- Remove volumes by adding the `-v` flag as shown in the Makefile.

## Next Steps
Phase 1 delivers the environment skeleton. Subsequent phases (schemas, orchestrator, UX) build on these services. Phase 4 adds Prefect orchestration and real LLM provider adapters—update `.env` with your OpenAI/Gemini API keys and model names to enable live calls.
