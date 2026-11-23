# T-047: Foundation follow-up: the Keelstart brand and support wording without reply times

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 (merged) |
| **ADRs** | [ADR-0041](../docs/adr/0041-brand-keelstart-everywhere-customers-look.md), [ADR-0042](../docs/adr/0042-support-wording-no-promised-reply-times.md), [ADR-0038](../docs/adr/0038-plans-v2-free-launch-team-and-plan-settings.md), [ADR-0021](../docs/adr/0021-settings-environments-and-production-guards.md), [ADR-0001](../docs/adr/0001-record-architecture-decisions.md) |
| **Status** | merged |

## Goal

The product owner renamed the product **Keelstart** and dropped promised support reply
times after T-001 merged. After this ticket the backend's default brand is "Keelstart"
(every page, email, PDF and export that reads the setting follows), and the three plans
say "Email support" / "Email support" / "Priority support" with no reply time.

## Owns (only these paths may change)

- `launch_agents/domain/constants.py`
- `launch_agents/domain/billing.py`
- `.env.example`
- `tests/test_foundation.py`
- `evidence/T-047/`
- `prs/T-047.md`

## Contracts

- **Provides:** `BRAND_NAME = "Keelstart"` (ADR-0041; the only spelling of the name in
  `launch_agents/`); the ADR-0042 `support_label` values in `_PLAN_BASE` (Free "Email
  support", Launch "Email support", Team "Priority support"), which also become the last
  item of each plan's `highlights`. No signature, type, enum value or field changes:
  `SupportLevel`, `Plan`, `build_plans`, `PLANS`, `Settings.brand_name` and every other
  T-001 contract stay exactly as merged.
- **Consumes:** the merged T-001 code (`config.py`, `agents/manager/greeting.py`,
  `pdf/render.py` stub defaults all read `BRAND_NAME` already; do not edit them).

## Acceptance criteria

1. `BRAND_NAME == "Keelstart"`; the comment above it cites ADR-0041 (the owner's rename).
   `load_settings({})` gives `brand_name == "Keelstart"`; `BRAND_NAME=Acme` in the env
   still overrides it.
2. Brand guard (updated T-001 criterion 16): a test scans every `.py` file in
   `launch_agents/` and finds the literal "Keelstart" only in `domain/constants.py`, and
   finds the old name "Charterly" in no file under `launch_agents/` and not in
   `.env.example`.
3. `manager_greeting()` contains "the Manager at Keelstart" (the greeting module itself is
   unchanged; the test asserts against `BRAND_NAME`).
4. `inspect.signature` of `render_signed_pdf` and `render_docx` shows the default
   `brand_name='Keelstart'` (still the `BRAND_NAME` constant).
5. `PLANS[...].support_label` is "Email support" (Free), "Email support" (Launch) and
   "Priority support" (Team); `support` levels stay `BASIC` / `STANDARD` / `PRIORITY`;
   each label is the last highlight of its plan.
6. No-promise check (ADR-0042): no `support_label` or highlight of any plan built with
   default or overridden amounts contains any ADR-0042 reply-time phrase ("reply within",
   "respond within", "response time", "business day", "same day", "answered first",
   case-insensitive). The comment "Support labels pending Q-009" in
   `billing.py` is replaced by a reference to ADR-0042.
7. `.env.example`: `BRAND_NAME=Keelstart` with the comment pointing to ADR-0041;
   nothing else in the file changes; the existing `.env.example` tests still pass.
8. Every other foundation test still passes unchanged in intent; only literals that
   spelled the old brand or the old support labels change.
   `bash scripts/py.sh -m pytest` passes with no network access.

## Feature run (`evidence/T-047/feature_run.py`)

Prints and asserts, without network: `BRAND_NAME` and `load_settings({}).brand_name`
(both "Keelstart") and an env override; the Manager greeting; the default `brand_name`
of `render_signed_pdf` / `render_docx` from `inspect.signature`; the three plans from
`Settings.plans()` with name, `support`, `support_label` and highlights; the
no-promise phrase check over every label and highlight; and the result of the brand
scan over `launch_agents/` (files containing "Keelstart", files containing "Charterly":
none).

## Out of scope

Any other change to T-001 code; the frontend brand kit and logo (T-011); email, PDF,
pricing and Terms copy (T-028, T-031, T-043); the founder-id high-water-mark follow-up
noted in T-001.
