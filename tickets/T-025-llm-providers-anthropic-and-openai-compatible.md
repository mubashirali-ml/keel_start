# T-025: LLM providers for production: `anthropic` (official SDK) and `deepseek` / `groq` (OpenAI-compatible)

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0022](../docs/adr/0022-llm-providers-fake-claude-code-anthropic-deepseek-groq.md), [ADR-0010](../docs/adr/0010-llm-provider-abstraction-and-fake.md), [ADR-0021](../docs/adr/0021-settings-environments-and-production-guards.md), [ADR-0023](../docs/adr/0023-reliability-timeouts-retries-and-failure-states.md) |
| **Status** | todo |

## Goal

In production every agent runs on an API key: `LLM_PROVIDER=anthropic` uses the official
`anthropic` SDK with `ANTHROPIC_API_KEY` (default model `claude-opus-5-5`, a cheaper
model per agent by configuration), and `deepseek` / `groq` remain as lower-cost options.

## Owns (only these paths may change)

- `launch_agents/llm/anthropic_provider.py`
- `launch_agents/llm/openai_compat.py`
- `tests/test_llm_anthropic.py`
- `tests/test_llm_openai_compat.py`
- `evidence/T-025/`
- `prs/T-025.md`

## Contracts

- **Provides:** `AnthropicProvider(settings, *, client=None)` and `OpenAICompatibleProvider(settings, *, preset=None, chat_model=None)` implementing `LLMProvider` (ADR-0022).
- **Consumes:** `LLMRequest`, `LLMProvider`, `LLMOutputError`, `report_usage`, `LLMUsage` (T-001), `Settings.model_for` / `effort_for` (T-001), packages `anthropic` and `langchain-openai`.

## Acceptance criteria

1. `AnthropicProvider` builds `anthropic.Anthropic(api_key, timeout=llm_timeout_s, max_retries=llm_max_retries)` unless a client is injected; tests inject a fake client object (no network) and assert the exact keyword arguments of each call.
2. Requests: system messages -> `system`; others -> `messages`; `model = settings.model_for(task) or "claude-opus-5-5"` (e.g. `LLM_MODEL_QA=claude-haiku-5-5` makes `qa.review` use Haiku); `max_tokens = request.max_tokens or 16000`; `output_config={"effort": settings.effort_for(task)}`; **no** `temperature`/`top_p`/`top_k` is sent.
3. `complete_json` uses structured outputs (`output_config.format` with the JSON schema of the pydantic model, or the SDK `messages.parse` helper), validates with `model_validate`, retries once with the validation error, then raises `LLMOutputError`.
4. `stop_reason` `refusal` or `max_tokens` -> `LLMOutputError` with a friendly message; SDK `APIConnectionError`, `APITimeoutError`, `RateLimitError`, `APIStatusError` -> `LLMOutputError`; the log line includes the SDK request id and never the key.
5. Opus-family models send the server-side refusal fallback (beta `server-side-fallback-2026-07-01`, `fallbacks="default"`) unless `ANTHROPIC_REFUSAL_FALLBACK=0`; Haiku models never send it.
6. Usage: one `LLMUsage` per attempt with `input_tokens`/`output_tokens` from `response.usage`.
7. `OpenAICompatibleProvider` keeps the ADR-0010 behaviour (JSON mode, fence stripping, one retry on invalid JSON) with the presets for `deepseek` and `groq`, `openai-compatible` via `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL`, per-agent `model_for`, timeout and `max_retries`, and usage reporting; tested with an injected `langchain_core` fake chat model.
8. `get_llm(settings)` (T-001) returns these classes for `anthropic`, `deepseek`, `groq`, `openai-compatible` and they construct without network access.
9. An optional live check runs only when `LAUNCH_LIVE_ANTHROPIC=1` and a key are set; it is excluded from the gate.

## Feature run (`evidence/T-025/feature_run.py`)

With a recording fake Anthropic client: prints the request arguments for a Manager text
call (Opus 5.5, effort, fallback beta) and a QA JSON call (Haiku via `LLM_MODEL_QA`,
structured output schema, no fallback), the parsed results and usage, a refusal and a
connection error turned into friendly `LLMOutputError`s; then a DeepSeek-preset call
through a fake chat model returning fenced JSON. Keys are shown redacted. If
`LAUNCH_LIVE_ANTHROPIC=1` is set it makes one real call and prints the model and token
counts (not required for the gate).

## Out of scope

The CLI provider (T-024), metering and usage limits (T-032), provider selection (T-001).
