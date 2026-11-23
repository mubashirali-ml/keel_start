# ADR-0013: Deterministic rules: case validation, cap table and vesting

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-002 (validation), T-003 (cap table, vesting, exports); consumed by T-006, T-012, T-014, T-015 |
| **Scope** | `launch_agents/rules/`, `launch_agents/domain/cap_table.py` |

## Context

The brief says validation is deterministic code, not the LLM: equity totals exactly 100%,
each cliff no longer than its vesting, 83(b) deadline = incorporation date + 30 days,
default vesting 48/12 stated to the user. The cap table splits exactly 10,000,000 shares
(units for an LLC), and vesting is monthly with a cliff. Documents must quote the same
share counts, so there must be exactly one implementation.

## Decision

### Validation (`rules/validation.py`, T-002)

`ValidationIssue` and `ValidationResult` live in `domain/types.py` (T-001) so views can
use them without importing `rules`; `rules/validation.py` re-exports them.

```python
class ValidationIssue(BaseModel):
    code: str; field: str; message: str; founder_id: str | None = None
class ValidationResult(BaseModel):
    ok: bool                         # no issues and nothing required missing
    issues: list[ValidationIssue]
    missing: list[str]               # required fact keys still unknown, in ask order
    facts: CaseFacts                 # normalised copy with vesting defaults applied
    notes: list[str]                 # founder-facing notes, e.g. default vesting
def apply_vesting_defaults(facts: CaseFacts) -> tuple[CaseFacts, list[str]]
def missing_facts(facts: CaseFacts) -> list[str]
def validate_facts(facts: CaseFacts) -> ValidationResult
```

Required facts, in the order the Manager asks: `business_description`, `entity_type`,
`state`, `founders`, `incorporation_date`. (`name_preferences` and `website` are optional.)
`founders` counts as missing when the list is empty.

Issue codes (binding; messages are friendly English naming the founder):

| code | rule |
|---|---|
| `equity_total` | founders present and sum of `equity_percent` != exactly 100 (Decimal compare). Message states the current total, e.g. "Equity adds up to 90%; it must total exactly 100%." |
| `equity_range` | any `equity_percent` <= 0 or > 100 |
| `equity_precision` | more than `EQUITY_DECIMALS` decimal places |
| `cliff_exceeds_vesting` | `cliff_months > vesting_months` (after defaults) |
| `vesting_range` | `vesting_months` < 0 or > 120, or `cliff_months` < 0 |
| `founder_name_missing` / `founder_email_invalid` / `founder_email_duplicate` | per founder |
| `invalid_state` | `state` not in `US_STATES` |
| `entity_state_mismatch` | `entity_type == C_CORP` and `state != "DE"` |

Vesting defaults: when **both** `vesting_months` and `cliff_months` are `None`, use 48/12;
when only `vesting_months` is given, cliff defaults to `min(12, vesting_months)`; when only
`cliff_months` is given, vesting defaults to 48. Each defaulted founder adds one note:
`"No vesting was given for {name}, so I used the standard 48 months with a 12-month cliff."`
`vesting_months == 0` means fully vested at the start (cliff must then be 0).

83(b): `domain.helpers.deadline_83b(incorporation_date)` = date + 30 calendar days
(not moved for weekends; the guide says "file early"). Days left: `days_until(deadline, today)`.

### Cap table (`domain/cap_table.py` types, T-001; `rules/cap_table.py`, T-003)

```python
class VestingEvent(BaseModel):
    month: int                  # 0 = start (only when vesting_months == 0), else 1..vesting_months
    date: date                  # add_months(start, month)
    vested_this_event: int
    cumulative_vested: int
class CapTableRow(BaseModel):
    founder_id: str; name: str; email: str
    equity_percent: Decimal; shares: int
    vesting_months: int; cliff_months: int
    schedule: list[VestingEvent]        # only events where vested_this_event > 0
class CapTable(BaseModel):
    entity_type: EntityType
    unit_label: Literal["shares", "units"]   # "units" for LLC
    authorized: int = AUTHORIZED_SHARES
    vesting_start: date                       # = incorporation_date
    rows: list[CapTableRow]                   # founder order
    total_issued: int                         # always == authorized
def build_cap_table(facts: CaseFacts) -> CapTable
    # Expects facts already normalised by validate_facts (callers validate first).
    # Raises FactsNotReadyError itself (no call into rules.validation) when: no founders,
    # equity does not sum to exactly 100, entity_type or incorporation_date missing,
    # or any founder's vesting_months/cliff_months is None.
def allocate_shares(percents: Sequence[Decimal], total: int = AUTHORIZED_SHARES) -> list[int]
def vesting_schedule(total: int, vesting_months: int, cliff_months: int, start: date) -> list[VestingEvent]
```

**Allocation** (largest remainder): `exact_i = total * p_i / 100` (Decimal);
`base_i = floor(exact_i)`; distribute `total - sum(base)` one share each to the largest
fractional parts, ties broken by founder order. Sum is always exactly `total`.

**Vesting** (monthly with cliff, cumulative-floor so no share is lost):
`cum(k) = 0` for `k < cliff`; `cum(k) = floor(total * k / vesting_months)` for
`cliff <= k < vesting_months`; `cum(vesting_months) = total`. Month `k` vests
`cum(k) - cum(k-1)`. So nothing vests before the cliff, the accrued portion vests at the
cliff month, then the rest monthly; the last event brings the founder to exactly `total`.
`vesting_months == 0` -> one event at month 0 for `total`. Vesting start is the
incorporation date (product default, see open question Q-004).

### Exports (`rules/exports.py`, T-003)

```python
def cap_table_csv(cap: CapTable) -> str     # header: Founder,Email,Equity %,Shares|Units,Vesting months,Cliff months,Fully vested on
def cap_table_xlsx(cap: CapTable) -> bytes  # sheets "Cap table" (same columns + total row) and "Vesting" (founder, month, date, vested, cumulative)
```

CSV uses `\n` line endings and UTF-8; numbers are plain integers (no thousands separators).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Largest remainder + cumulative-floor vesting (chosen) | Exact totals by construction; easy to prove in tests | Rounding favours earlier founders on ties |
| B. Round each founder, put the difference on the last founder | Simple | Arbitrary; can be off by more than one share |
| C. Even monthly amounts with the remainder in the last month | Familiar | Cliff amount no longer equals the accrued portion |

## Consequences

- Law documents and the UI quote `CapTable.rows[i].shares`; they never compute shares.
- A founder-facing number is always an integer share count; percentages are displayed with
  at most two decimals.
