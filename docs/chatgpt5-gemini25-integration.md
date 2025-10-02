# Integrating GPT-5 & Gemini 2.5 (Pro & Flash) into Book Creator

This note distills the latest publicly documented capabilities for OpenAI’s **GPT‑5** family and Google’s **Gemini 2.5** models (Pro & Flash) into concrete implementation steps for the Book Creator stack.

## 1. OpenAI GPT‑5 (ChatGPT 5) API

### 1.1 Model lineup & limits
- API models: `gpt-5` (reasoning), `gpt-5-mini`, `gpt-5-nano`, and the non-reasoning router `gpt-5-chat-latest` for ChatGPT parity.[^openai-dev]
- Context window: **272,000 input tokens + 128,000 reasoning/output tokens** (400k total).[^openai-dev]
- Supported endpoints: Responses API, Chat Completions API, Codex CLI default.[^openai-dev]

### 1.2 New parameters & tooling
- `reasoning_effort`: `{minimal, low, medium (default), high}`. `minimal` trims deliberation for quicker but cheaper answers; `high` uses more tokens/time.[^openai-dev]
- `verbosity`: `{low, medium (default), high}` to bias answer length. Explicit instructions (e.g., “write 5 paragraphs”) still dominate.
- **Custom tools**: GPT‑5 can emit plaintext payloads for developer tools (no JSON escaping) while retaining structured outputs, streaming, prompt caching, Batch API, built-in tools (search, image, files), and parallel tool calls.[^openai-dev]

### 1.3 Pricing snapshot (September 2025)

| Model | Input (USD / 1M tokens) | Output (USD / 1M tokens) |
| --- | --- | --- |
| `gpt-5` | $1.25 | $10.00 |
| `gpt-5-mini` | $0.25 | $2.00 |
| `gpt-5-nano` | $0.05 | $0.40 |
| `gpt-5-chat-latest` | $1.25 | $10.00 |

### 1.4 Integration checklist (Book Creator)
1. **Provider configuration** (`libs/python/book_creator_providers`)
   - Register all four GPT‑5 identifiers with the 400k context window and default `reasoning_effort="medium"`, `verbosity="medium"`.
   - Flag capabilities (`supports_custom_tools`, `supports_prompt_caching`, `supports_structured_outputs`).
2. **Settings UI** (`apps/frontend/src/pages/provider-settings.tsx`)
   - Surface GPT‑5 models with pricing tooltips and sliders/dropdowns for `reasoning_effort` & `verbosity`.
3. **Orchestrator overrides** (stage engines + `services/orchestrator/app/providers.py`)
   - Allow per-stage overrides: e.g. `minimal` for ideation/title drafts, `high` for fact mapping/guidelines.
   - Default `verbosity="low"` for tool-heavy stages to reduce response bloat; raise when narrative output is desired.
   - Enable plaintext custom tool payloads when streaming large JSON/code to reduce escaping failures.
4. **Config/ENV**: existing OpenAI API key + host suffice; only the model strings & optional defaults change.
5. **Testing**: refresh regression fixtures (schemas, emotional layer, guidelines) to confirm GPT‑5 structured outputs stay within expected schemas at different reasoning settings.

[^openai-dev]: “Introducing GPT‑5 for developers”, OpenAI (https://openai.com/index/introducing-gpt-5-for-developers/), retrieved via https://r.jina.ai/.

## 2. Google Gemini 2.5 (Pro & Flash)

### 2.1 Model profiles
- **Gemini 2.5 Pro** (`gemini-2.5-pro`)
  - Modalities: inputs of audio, images, video, text, PDF; text output.[^gemini-models]
  - Limits: **1,048,576 input tokens / 65,536 output tokens**; supports Batch API, caching, function calling, structured outputs, URL context, Search grounding, “thinking” mode.[^gemini-models]
  - Knowledge cutoff: January 2025; last update June 2025.
- **Gemini 2.5 Flash** (`gemini-2.5-flash`)
  - Optimised for high-throughput, lower-latency tasks with the same 1M/65k context, multimodal inputs, thinking support, and agentic tooling as Pro, but lower price points.[^gemini-models]

### 2.2 Thinking configuration & budgets
- Requests use `generationConfig.thinkingConfig` (REST) / `ThinkingConfig` (SDKs) with:
  - `thinkingBudget` (tokens): guides internal reasoning depth. Billing counts the thinking tokens at output rates.[^gemini-thinking]
  - `thinkingBudget = -1`: dynamic mode (model decides budget). For Flash & Flash Preview the dynamic range is `0–24,576`; Pro ranges `128–32,768` and always thinks (cannot disable).[^gemini-thinking]
  - `thinkingBudget = 0`: disable thinking (Flash/Flash Preview only) for lowest latency tasks.
  - `includeThoughts = true`: return thought summaries (optional, not billed as thinking tokens).[^gemini-thinking]
- Recommended defaults (per Google):
  - Light prompts: Flash with budget `512–1,024` tokens.
  - Complex reasoning/coding: Pro with budget `4,096–16,384` or dynamic (`-1`).
  - Latency-sensitive workflows: Flash with budget `0–256` or dynamic on alternate retries.

### 2.3 Pricing snapshot (September 2025)

**Gemini 2.5 Pro** (Paid tier)[^gemini-pricing]

- Input tokens: $1.25 / 1M (≤200k-token prompts), $2.50 / 1M (>200k).
- Output tokens (includes thinking): $10.00 / 1M (≤200k), $15.00 / 1M (>200k).
- Context caching: $0.31 / 1M cached tokens (≤200k), $0.625 / 1M (>200k), storage $4.50 / 1M tokens-hour.
- Grounded search add-on: 1,500 requests/day free, then $35 / 1,000.

**Gemini 2.5 Flash** (Paid tier)[^gemini-pricing]

- Input tokens: $0.30 / 1M (text/image/video), $1.00 / 1M (audio).
- Output tokens (includes thinking): $2.50 / 1M.
- Context caching: $0.075 / 1M cached tokens (text/image/video), $0.25 / 1M (audio), storage $1.00 / 1M tokens-hour.
- Grounded search add-on: 1,500 requests/day free (shared with Flash-Lite), then $35 / 1,000.

*Free tier provides limited usage of both Pro and Flash with zero-cost tokens up to Google’s published caps.*

### 2.4 Integration checklist (Book Creator)
1. **Provider configuration**
   - Add `gemini-2.5-pro` and `gemini-2.5-flash` (plus optional `gemini-2.5-pro-preview-tts`) with context limits, modality flags, pricing metadata, and capability booleans (`supports_thinking`, `supports_grounding`, `supports_function_calling`, `supports_multimodal_inputs`).
   - Expose default `thinkingBudget` (e.g., `1024`) and `includeThoughts` toggles in provider overrides.
2. **API payloads**
   - REST/SDK: include `generationConfig.thinkingConfig` with `thinkingBudget` or `-1` for dynamic thinking. Add `includeThoughts` when debugging reasoning traces.
   - Map Book Creator stage preferences to budgets (e.g., guidelines high budget, ideation low/dynamic, bulk summarisation zero).
   - Enable `tools` (function declarations) and `groundingConfig` when orchestrator requests require tool use or Google Search grounding.
3. **UI / workflow**
   - Provider settings page: display both Pro and Flash with modal differences (cost, latency) and sliders for thinking budget / dynamic toggle.
   - Emotional/guideline labs: allow editors to bump budget inline when responses need deeper reasoning.
4. **Fallback & quotas**
   - Keep Gemini 1.5 variants configured as automatic fallbacks (quota/region hedging). Orchestrator should downgrade on quota errors and notify operators.
5. **Cost controls**
   - Surfacing prompt caching switches (Paid only) and log thinking token consumption in observability dashboards to guard runaway costs.
6. **Testing**
   - Add integration fixtures that cover multimodal requests, large-context prompts (>200k tokens), and different thinking budgets to confirm schema compliance and budget enforcement.

[^gemini-models]: “Gemini Models”, Google AI (https://ai.google.dev/gemini-api/docs/models#gemini-2.5-pro), retrieved via https://r.jina.ai/.
[^gemini-thinking]: “Gemini thinking”, Google AI (https://ai.google.dev/gemini-api/docs/thinking), retrieved via https://r.jina.ai/.
[^gemini-pricing]: “Gemini Developer API Pricing”, Google AI (https://ai.google.dev/gemini-api/docs/pricing), retrieved via https://r.jina.ai/.

## 3. Operational Considerations
- **Observability**: track GPT‑5 `reasoning_effort`/`verbosity` and Gemini `thinkingBudget`, `includeThoughts`, and thinking token spend in Phase 15 dashboards.
- **Prompt design**: document recommended defaults per stage (e.g., GPT‑5 `high` reasoning for fact mapping, Gemini budgets for guidelines) and how to escalate/downgrade on retries.
- **Rate limits & fallbacks**: parameterise RPM/TPM ceilings so DevOps can tune without code deploy; surface automatic downgrade events in alerts.
- **Compliance & messaging**: update customer docs to highlight new data-handling differences (Gemini Free tier training usage vs. Paid opt-out) and updated pricing.

With these steps, Book Creator can adopt the latest reasoning-grade models while preserving the existing provider abstraction and cost controls established in earlier phases.
