# T-002: Case validation rules (equity, vesting, 83(b), missing facts)

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md), [ADR-0007](../docs/adr/0007-stack-and-module-layout.md) |
| **Status** | todo |

## Goal

The Manager, the services and the UI can ask one deterministic module whether the case
facts are valid and complete, get friendly issue messages, and get vesting defaults
applied and announced.

## Owns (only these paths may change)

- `launch_agents/rules/validation.py`
- `tests/test_validation.py`
- `evidence/T-002/`
- `prs/T-002.md`

## Contracts

- **Provides:** `apply_vesting_defaults(facts) -> tuple[CaseFacts, list[str]]`, `missing_facts(facts) -> list[str]`, `validate_facts(facts) -> ValidationResult`; re-exports `ValidationIssue`, `ValidationResult` (ADR-0013).
- **Consumes:** `CaseFacts`, `Founder`, constants, `US_STATES`, `deadline_83b` (T-001).

## Acceptance criteria

1. Equity: 60/40 ok; 60/30 -> `equity_total` whose message says the total is 90%; 33.33/33.33/33.34 ok; 0% or 101% -> `equity_range`; 33.333 -> `equity_precision`. Comparison is exact `Decimal`, never float.
2. Vesting: both missing -> 48/12 + one note per founder naming them; only vesting 24 -> cliff 12; only vesting 6 -> cliff 6; only cliff 6 -> vesting 48; cliff 13 with vesting 12 -> `cliff_exceeds_vesting` naming the founder; 0/0 valid; negative or > 120 -> `vesting_range`.
3. Founders: missing name, invalid email, duplicate email (case-insensitive) each produce their own code with `founder_id` set.
4. State: unknown code -> `invalid_state`; `Delaware C-Corp` with `state="WY"` -> `entity_state_mismatch`.
5. `missing_facts` returns keys in the ADR order and never lists optional facts; `ok` is False while anything is missing or any issue exists.
6. `validate_facts` is pure (input not mutated) and its `facts` has defaults applied.
7. Every issue message is a friendly sentence without field codes or JSON.

## Feature run (`evidence/T-002/feature_run.py`)

Validates five printed scenarios end to end and asserts the outcome of each: the sample
two-founder LLC (ok, with the default-vesting note for Bob), equity summing to 90%, a
cliff longer than vesting, a C-Corp in Wyoming, and a half-filled case (prints the
missing facts in ask order). Also prints the 83(b) deadline for the sample.

## Out of scope

Cap table math (T-003); deciding what the Manager says (T-012).
