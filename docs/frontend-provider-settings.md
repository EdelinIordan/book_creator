# Agents & API Settings Notes

## Goals
- Allow users to manage OpenAI, Gemini, or mock API keys and defaults from the UI.
- Configure per-agent overrides aligned with the roster defined in "User app description and Agents Roster".
- Persist configuration locally until backend endpoints are implemented.
- Provide hints about how overrides map to orchestrator payloads.

## Current State (Phase 9)
- Menu entry **Agents & API** replaces the earlier Provider Settings page.
- Form fields: provider selection, API key, default model, temperature, top‑p, GPT‑5 reasoning effort & verbosity, Gemini thinking budget, and include-thought toggles.
- Model catalog ships GPT‑5 (`gpt-5`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5-chat-latest`) and Gemini 2.5 (`gemini-2.5-pro`, `gemini-2.5-flash`) presets plus legacy fallbacks.
- Agent roster table: each agent exposes provider/model selection, sampling controls (temperature & top‑p), reasoning effort/verbosity for OpenAI, Gemini thinking budget/thought toggle, and max tokens with local overrides.
- On save: values are persisted in `localStorage` (`book-creator-provider-settings` and `book-creator-agent-settings`).
- Messaging indicates backend integration is a roadmap item.

## Roadmap Integration
- Expose REST endpoints in API gateway to store encrypted provider credentials and agent overrides.
- Sync overrides to orchestrator’s `ProviderOverride` schema per agent.
- Add validation to prevent duplicate agent allocations and surface real-time cost estimates.
- Extend dashboard cards to show which provider/models are active per project and per agent.

## UI Enhancements
- Toast notifications for success/error once backend is connected.
- Inline cost/budget estimation using metrics from Phase 15.
- Toggle between workspace defaults and project-level agent overrides when persistence is available.
