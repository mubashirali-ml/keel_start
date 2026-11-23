# T-024: LLM provider `claude_code`: the Claude Code CLI in print mode for local development and live demos

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0022](../docs/adr/0022-llm-providers-fake-claude-code-anthropic-deepseek-groq.md), [ADR-0010](../docs/adr/0010-llm-provider-abstraction-and-fake.md), [ADR-0021](../docs/adr/0021-settings-environments-and-production-guards.md), [ADR-0023](../docs/adr/0023-reliability-timeouts-retries-and-failure-states.md) |
| **Status** | todo |

## Goal

With `LLM_PROVIDER=claude_code` the owner runs every agent on their own machine through
the Claude Code CLI bundled with the VS Code extension and their own login, with no API
key; the provider warns at startup that this is for the owner's own use only and refuses
to run in production.

## Owns (only these paths may change)

- `launch_agents/llm/claude_code.py`
- `tests/test_llm_claude_code.py`
- `evidence/T-024/`
- `prs/T-024.md`

## Contracts

- **Provides:** `ClaudeCodeProvider(settings, *, runner=None, binary=None)` implementing `LLMProvider` (`name = "claude_code"`, `complete`, `complete_json`); `find_claude_binary(settings, *, home=None)` (ADR-0022).
- **Consumes:** `LLMRequest`, `LLMMessage`, `LLMProvider`, `LLMOutputError`, `report_usage`, `LLMUsage` (T-001 `llm/`), `Settings`, `AppEnv`, `ConfigError` (T-001 `config.py`), `call_with_retry` (T-001). Standard library only (`subprocess`, `json`, `shutil`, `pathlib`, `logging`).

## Acceptance criteria

1. `find_claude_binary`: `CLAUDE_CODE_PATH` wins; else the newest `~/.vscode/extensions/anthropic.claude-code-<version>-<platform>/resources/native-binary/claude(.exe)` by numeric version (tested with a temp `home` holding `2.1.9`, `2.1.330` and `2.1.40` folders: picks 2.1.330); else `shutil.which("claude")`; else `ConfigError` naming the three options.
2. Command line built exactly per ADR-0022: list form (never `shell=True`), `-p <prompt> --output-format json --tools "" --system-prompt <system> --max-turns 3`, `--json-schema <schema>` for `complete_json`, `--model <id>` only when `settings.model_for(task)` is set; stdin closed; prompts over 24,000 characters go through stdin instead of the argument (both paths tested with a fake runner).
3. The child environment has `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` removed and everything else kept.
4. Result parsing from recorded sample outputs (fixtures in the test file, matching CLI 2.1.330): text -> `result`; schema -> `structured_output` validated with the pydantic schema; missing `structured_output` -> `LLMOutputError`; invalid structured output -> one retry with the validation error in the prompt, then `LLMOutputError`; `is_error: true`, non-zero exit, unparseable stdout and `subprocess.TimeoutExpired` (`CLAUDE_CODE_TIMEOUT_S`) -> `LLMOutputError` with the clear messages of ADR-0022 (a "not logged in" hint when stderr says so).
5. One retry on a non-zero exit or `is_error`, none on timeout (ADR-0023).
6. Usage: one `LLMUsage` per attempt with tokens from the JSON `usage` block when present, `ok` False on failures, duration measured.
7. Policy: constructing the provider logs the ADR-0022 warning exactly once per process (tested with `caplog`); `settings.app_env == production` raises `ConfigError`.
8. Rendering: system messages joined into `--system-prompt`; the transcript of the remaining messages is labelled ("Founder:", "Assistant:") and ends with the last user message; JSON-schema calls add one line asking for the schema only.
9. No test calls the real CLI. An optional live check runs only when `LAUNCH_LIVE_CLAUDE_CODE=1` is set and is excluded from the gate.

## Feature run (`evidence/T-024/feature_run.py`)

With a fake runner that records the command and returns recorded CLI JSON: prints the
binary resolution for a temp extensions folder, the exact argument list (prompt
truncated) and the scrubbed environment keys for one `complete` and one `complete_json`
call (a `RouteDecision`-shaped schema), the parsed results and the usage records, then
the error paths (timeout, `is_error`, missing `structured_output`) with their messages,
the startup warning, and the `ConfigError` for `APP_ENV=production`. If
`LAUNCH_LIVE_CLAUDE_CODE=1` is set it also makes one real call and prints its duration
(not required for the gate).

## Out of scope

The Anthropic SDK provider (T-025), provider selection (T-001), metering (T-032).
