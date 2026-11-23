# ADR-0022: LLM providers: fake, claude_code, anthropic, deepseek, groq

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor, product owner |
| **Tickets** | T-001 (selection, stubs, usage reporting), T-024 (claude_code), T-025 (anthropic, openai-compatible) |
| **Scope** | `launch_agents/llm/` |

## Context

ADR-0010 fixed the `LLMProvider` interface, the deterministic `FakeLLM` and the task
catalog, with DeepSeek/Groq as the only real providers. The product owner now wants one
setting, `LLM_PROVIDER`, to choose between five backends (brief, "LLM providers"):
`fake` for tests and the reliable demo; `claude_code` for development and live demos on
the owner's own machine through the Claude Code CLI bundled with the VS Code extension
(no API key); `anthropic` for production through the official SDK; `deepseek` and `groq`
as lower-cost alternatives. Anthropic's terms allow a subscription login only for the
owner's own use. This ADR **supersedes the provider and configuration part of ADR-0010**
(sections "Real provider" and "Configuration"); the interface, the fake, the
`complete_json` contract and the task catalog of ADR-0010 remain in force.

## Decision

### Selection (`llm/__init__.py: get_llm(settings) -> LLMProvider`, T-001)

| `LLM_PROVIDER` | Class (module, ticket) | Credential | Default model |
|---|---|---|---|
| `fake` | `FakeLLM` (`llm/fake.py`, T-001) | none | — |
| `claude_code` | `ClaudeCodeProvider` (`llm/claude_code.py`, T-024) | the owner's Claude Code login | the CLI's default unless `LLM_MODEL[_<AGENT>]` is set |
| `anthropic` | `AnthropicProvider` (`llm/anthropic_provider.py`, T-025) | `ANTHROPIC_API_KEY` | `claude-opus-5-5` |
| `deepseek` | `OpenAICompatibleProvider` preset (`llm/openai_compat.py`, T-025) | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| `groq` | same, preset | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| `openai-compatible` | same, `LLM_BASE_URL` + `LLM_API_KEY` | key | `LLM_MODEL` |

When `LLM_PROVIDER` is unset: `ANTHROPIC_API_KEY` -> `anthropic`, else `DEEPSEEK_API_KEY`
-> `deepseek`, else `GROQ_API_KEY` -> `groq`, else `fake`. `claude_code` is never chosen
implicitly. `LAUNCH_FAKE_SERVICES=1` forces `fake`. Production refuses `fake` and
`claude_code` (ADR-0021).

**Per-agent models.** The agent is the first segment of `LLMRequest.task`
(`"name.suggest"` -> `name`). Every real provider asks `settings.model_for(task)`:
`LLM_MODEL_<AGENT>` (e.g. `LLM_MODEL_NAME=claude-haiku-5-5`, `LLM_MODEL_QA=claude-haiku-5-5`),
else `LLM_MODEL`, else the provider default. `.env.example` shows the Haiku lines for the
Name and QA agents, commented out.

### Usage reporting (`llm/usage.py`, T-001)

```python
class LLMUsage(BaseModel):
    provider: str; model: str | None; task: str
    input_tokens: int | None = None; output_tokens: int | None = None
    duration_ms: int; ok: bool
def report_usage(usage: LLMUsage) -> None             # every provider calls this once per attempt
@contextmanager
def usage_sink(callback: Callable[[LLMUsage], None]) -> Iterator[None]   # ContextVar-scoped; nests
```

Providers never know which customer they serve; the metering wrapper (ADR-0033) opens a
`usage_sink` around each call. The fake reports usage with `None` tokens.

### `claude_code` (T-024): the Claude Code CLI in print mode

```python
class ClaudeCodeProvider:
    name = "claude_code"
    def __init__(self, settings: Settings, *, runner: Callable[..., subprocess.CompletedProcess] | None = None,
                 binary: str | None = None) -> None   # runner injectable for tests (default subprocess.run)
def find_claude_binary(settings: Settings, *, home: Path | None = None) -> str   # ConfigError if none
```

- **Binary:** `CLAUDE_CODE_PATH`; else the newest
  `~/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude(.exe)`
  (newest by the version in the folder name, compared numerically); else `claude` on
  `PATH`; else `ConfigError` explaining all three options.
- **Command** (stdlib `subprocess`, list form, never `shell=True`):
  `claude -p <prompt> --output-format json --tools "" --system-prompt <system> --max-turns 3`
  plus `--json-schema <schema json>` for `complete_json` and `--model <id>` when
  `model_for(task)` is set. `<system>` is the request's system messages joined; `<prompt>`
  renders the remaining messages as a labelled transcript ending with the last user
  message. Every request carries its whole history, so calls are independent and
  `--resume` (verified to work) is deliberately not used. stdin is closed
  (`stdin=subprocess.DEVNULL`); if the rendered prompt exceeds 24,000 characters (Windows
  command-line limit) the prompt argument is omitted and the prompt is written to stdin,
  which is then closed. The builder verifies this path on the CLI.
- **Environment:** a copy of `os.environ` with `ANTHROPIC_API_KEY` and
  `ANTHROPIC_AUTH_TOKEN` removed (either would take precedence over the login).
- **Result:** parse stdout as JSON. `is_error: true`, non-zero exit, unparseable output or
  a timeout (`CLAUDE_CODE_TIMEOUT_S`, default 120 s; 4–8 s is typical) raise
  `LLMOutputError` with a clear message ("Claude Code did not answer within 120 s",
  "Claude Code is not logged in: run `claude` once and sign in"). Text calls return
  `result`; schema calls read `structured_output` (missing field -> `LLMOutputError`),
  then validate with the pydantic schema (one retry with the validation error, ADR-0010).
  Usage is reported from the JSON `usage` block when present.
- **Policy:** the constructor logs a WARNING once per process: "LLM_PROVIDER=claude_code
  uses your personal Claude Code login. Anthropic's terms allow this only for your own
  local development and demos, never for serving other users. Use LLM_PROVIDER=anthropic
  with an API key for anything other people use." It raises `ConfigError` when
  `settings.app_env == production` (defence in depth behind ADR-0021).
- Retries: one retry on a non-zero exit or `is_error` (not on timeout), per ADR-0023.

### `anthropic` (T-025): official `anthropic` SDK with `ANTHROPIC_API_KEY`

```python
class AnthropicProvider:
    name = "anthropic"
    def __init__(self, settings: Settings, *, client: "anthropic.Anthropic | None" = None) -> None
```

- Client: `anthropic.Anthropic(api_key=..., timeout=settings.llm_timeout_s,
  max_retries=settings.llm_max_retries)` (the SDK retries 408/409/429/5xx and connection
  errors with backoff). Model `model_for(task)` or `claude-opus-5-5`.
- Requests: system messages go to `system`, the rest to `messages`; `max_tokens` =
  `request.max_tokens or 16000`; `output_config={"effort": settings.effort_for(task)}`
  (default `medium`, Opus 5.5's own default). `LLMRequest.temperature` is **not sent**
  (current models reject sampling parameters) and thinking is left at the model default.
- `complete_json`: structured outputs, `output_config.format` with the JSON schema of the
  pydantic model (or the SDK's `messages.parse` helper), then `schema.model_validate`;
  one retry with the validation error appended; then `LLMOutputError`.
- `stop_reason == "refusal"` or `"max_tokens"` -> `LLMOutputError` with a friendly
  message; SDK errors (`APIConnectionError`, `RateLimitError`, `APIStatusError`, ...) ->
  `LLMOutputError`, logged with the SDK request id, never the key.
- Refusal fallback: for Opus-family models the request uses the server-side fallback
  (`client.beta.messages.create(..., betas=["server-side-fallback-2026-07-01"],
  fallbacks="default")`) unless `ANTHROPIC_REFUSAL_FALLBACK=0`; Haiku models have no
  server-side fallback and simply report the refusal.
- Usage from `response.usage.input_tokens` / `output_tokens`.

### `deepseek`, `groq`, `openai-compatible` (T-025)

Unchanged behaviour from ADR-0010 (`langchain_openai.ChatOpenAI`, JSON mode, fence
stripping), now constructed as
`OpenAICompatibleProvider(settings, *, preset: str | None = None, chat_model=None)` with
timeout `llm_timeout_s`, `max_retries=llm_max_retries`, `model_for(task)` and usage reporting.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Five providers behind the ADR-0010 interface, CLI via subprocess, SDK for production (chosen) | No new dependency for local use; production on an API key; agents unchanged | CLI output format must be tracked when Claude Code updates |
| B. Claude Agent SDK for local use | Typed | New dependency; still a subscription login |
| C. Anthropic through an OpenAI-compatible shim | One code path | Loses structured outputs, refusal handling and request ids |
| D. Allow `claude_code` in production | Cheaper for the owner | Violates Anthropic's terms; refused |

## Consequences

- The owner can run the live demo on their own machine with no API key; production
  needs `ANTHROPIC_API_KEY` (or another key) and cannot start otherwise.
- Agents, prompts and fakes do not change; only the provider classes are new.
- A CLI update that changes the JSON fields shows up as a clear `LLMOutputError`, and
  T-024's tests pin the expected shape with recorded sample outputs.
