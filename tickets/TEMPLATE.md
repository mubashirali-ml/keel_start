# T-NNN: <title>

| | |
|---|---|
| **Wave** | 0 / 1 / 2 … |
| **Depends on** | T-XXX (merged) or — |
| **ADRs** | [ADR-XXXX](../docs/adr/XXXX-....md), … |
| **Status** | todo / in_progress / in_review / merged / escalated |

## Goal

One or two sentences: what the user or caller can do after this ticket that they couldn't before.

## Owns (only these paths may change)

- `path/to/module/`
- `tests/test_something.py`
- `evidence/T-NNN/`, `prs/T-NNN.md` (always)

## Contracts

- **Provides:** signatures/types other tickets will call (with the ADR that defines them).
- **Consumes:** signatures/types from earlier tickets.

## Acceptance criteria

1. Concrete, testable statement.
2. …

## Feature run (`evidence/T-NNN/feature_run.py`)

What the recorded run must demonstrate end to end.

## Out of scope

What this ticket must not do (it belongs to another ticket).
