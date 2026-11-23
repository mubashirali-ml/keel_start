# T-003: Cap Table Builder: share allocation, vesting schedule, CSV and Excel export

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md), [ADR-0024](../docs/adr/0024-stack-and-module-layout-v2.md) |
| **Status** | todo |

## Goal

Given validated facts, the product can produce a cap table that always splits exactly
10,000,000 shares (units for an LLC), each founder's monthly vesting schedule with the
cliff, and CSV / Excel downloads.

## Owns (only these paths may change)

- `launch_agents/rules/cap_table.py`
- `launch_agents/rules/exports.py`
- `tests/test_cap_table.py`
- `tests/test_cap_table_exports.py`
- `evidence/T-003/`
- `prs/T-003.md`

## Contracts

- **Provides:** `build_cap_table(facts) -> CapTable`, `allocate_shares(percents, total=AUTHORIZED_SHARES) -> list[int]`, `vesting_schedule(total, vesting_months, cliff_months, start) -> list[VestingEvent]`, `cap_table_csv(cap) -> str`, `cap_table_xlsx(cap) -> bytes` (ADR-0013).
- **Consumes:** `CapTable`, `CapTableRow`, `VestingEvent`, `add_months`, `FactsNotReadyError` (T-001). Must not import `rules.validation` (built in parallel by T-002); callers pass normalised facts.

## Acceptance criteria

1. `allocate_shares` sums to exactly `total` for: 60/40, 50/50, 33.33/33.33/33.34, 1/99, ten founders at 10%, and a property-style loop over 200 random 2-decimal splits that sum to 100 (seeded RNG); ties are broken by founder order.
2. `unit_label` is `units` for LLC and `shares` for Delaware C-Corp; `total_issued == authorized == 10_000_000`.
3. Vesting for 4,800,000 shares, 48/12: months 1–11 vest nothing; month 12 vests 1,200,000; months 13–48 vest 100,000 each; cumulative at 48 equals the grant; dates step by `add_months` from the incorporation date (month-end clamping tested with a Jan-31 start).
4. Non-divisible totals (e.g. 3,333,333 over 48/12) never lose or invent a share; 0/0 vests everything at month 0; cliff == vesting vests everything at the cliff.
5. `build_cap_table` raises `FactsNotReadyError` (friendly message) for: no founders, equity not 100, missing entity type or incorporation date, any vesting value `None`.
6. CSV has the exact ADR header (Shares or Units), one row per founder, integer share counts, `\n` endings; Excel opens with openpyxl and has sheets "Cap table" (with a total row equal to 10,000,000) and "Vesting".

## Feature run (`evidence/T-003/feature_run.py`)

Builds the cap table for the sample LLC (defaults applied in the script itself), prints
the table and the first 14 and last 2 vesting events per founder, asserts the 10,000,000
total and the cliff behaviour, then a three-way 33.33/33.33/33.34 C-Corp split; writes the
CSV and XLSX to a temp dir, re-reads the XLSX with openpyxl and prints its sheet names
and total row.

## Out of scope

Validation messages (T-002); serving downloads over HTTP (T-017); the UI (T-021).
