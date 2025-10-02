# Provider Abstraction Usage

Phase 3 introduces `book_creator_providers`, a Python package that encapsulates
communication with Google Gemini 2.5 Pro and OpenAI ChatGPT 5. The orchestration
and worker services will depend on this package instead of talking to SDKs
directly.

## Installation

```bash
# install schemas + providers from libs/python
python -m pip install -e libs/python[providers]
```

## Environment Variables

The factory reads environment variables prefixed by the provider name:

- `LLM_PROVIDER` – selects default provider (`gemini`, `openai`, or `mock`).
- `<PROVIDER>_API_KEY` – API key (e.g., `OPENAI_API_KEY`).
- `<PROVIDER>_MODEL` – Model identifier (e.g., `gpt-5-mini`, `gemini-2.5-pro`).
- `<PROVIDER>_TEMPERATURE` – Optional float; defaults to `0.4`.
- `<PROVIDER>_MAX_OUTPUT_TOKENS` – Optional int.
- `<PROVIDER>_TOP_P` – Optional float.
- `<PROVIDER>_JSON_MODE` – `true` to enable JSON schema enforcement by default.

Example `.env` snippet:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-live-...
OPENAI_MODEL=gpt-5-mini
OPENAI_TEMPERATURE=0.3
```

## Basic Usage

```python
from book_creator_providers import ProviderFactory, ProviderRequest

provider = ProviderFactory.create()
response = await provider.generate(
    ProviderRequest(
        prompt="Summarise chapter 1",
        system_prompt="You are a helpful editor.",
        json_schema={"type": "object", "properties": {"summary": {"type": "string"}}},
    )
)
print(response.text)
```

For offline tests use the mock provider:

```python
from book_creator_providers import MockProvider, ProviderRequest

mock = MockProvider()
result = asyncio.run(mock.generate(ProviderRequest(prompt="Test")))
```

## Observability Hooks

Each `ProviderResponse` records prompt/completion tokens and latency. Phase 15
will consume these values for dashboards and cost tracking.

## Error Handling

- `ProviderConfigError` – thrown when required env vars are missing.
- `ProviderResponseError` – thrown when the provider returns an unexpected payload.

Wrap calls in the orchestrator to catch these exceptions and trigger retries or
fallbacks as needed.

## REST Endpoint (Orchestrator)

Phase 4 exposes a FastAPI endpoint: `POST http://localhost:9100/orchestrator/run`

```json
{
  "provider": {
    "name": "openai",
    "model": "gpt-5-mini",
    "temperature": 0.4
  },
  "stages": [
    {
      "stage": "IDEA",
      "prompt": "Summarise the user's book concept."
    }
  ]
}
```

Omitting the body (or the `stages` field) causes the orchestrator to use the default
stage prompts. Omitting `provider` falls back to the `LLM_PROVIDER` setting from
the environment (`mock` by default).

### Stage-Specific Overrides

Each stage entry can include its own `provider_override` block. This allows you to
route, for example, the structure stage to Gemini while keeping writing on OpenAI:

```json
{
  "provider": { "name": "openai", "model": "gpt-5" },
  "stages": [
    {
      "stage": "STRUCTURE",
      "prompt": "Outline the chapters",
      "provider_override": {
        "name": "gemini",
        "model": "gemini-2.5-pro",
        "temperature": 0.25,
        "thinking_budget": 4096,
        "include_thoughts": false
      }
    },
    {
      "stage": "WRITING",
      "prompt": "Draft the introduction",
      "provider_override": {
        "name": "openai",
        "model": "gpt-5",
        "reasoning_effort": "high",
        "verbosity": "medium"
      }
    }
  ]
}
```

### Managing API Keys from the UI (Roadmap)

Phase 6+ will surface a provider settings screen where you can store API keys,
choose default models, and map individual agents to preferred LLMs. Those values
will be persisted in the backend and supplied automatically to the orchestrator,
removing the need to edit `.env` manually.
