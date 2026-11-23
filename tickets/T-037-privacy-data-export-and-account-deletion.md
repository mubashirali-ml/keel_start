# T-037: Privacy: export all my data and delete my account

| | |
|---|---|
| **Wave** | 2 |
| **Depends on** | T-003, T-005, T-026, T-027, T-029, T-031, T-047 |
| **ADRs** | [ADR-0041](../docs/adr/0041-brand-keelstart-everywhere-customers-look.md), [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md), [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md) |
| **Status** | todo |

## Goal

A customer can download everything the product holds about them and their companies in
one zip, and can delete their account; companies they share with co-founders stay with
the co-founders (with the signed record intact), companies only they belong to are
deleted completely, and their subscription is cancelled.

## Owns (only these paths may change)

- `launch_agents/privacy/`
- `launch_agents/persistence/privacy.py`
- `tests/test_privacy.py`
- `evidence/T-037/`
- `prs/T-037.md`

## Contracts

- **Provides:** `PrivacyService` (`export_zip`, `delete_account`), `DeletionReport`, `PrivacyQueries` (ADR-0034).
- **Consumes:** `Repository` (T-005), `AccountsRepository` + `verify_password` (T-026), `TeamRepository` (T-027), `BillingService` (T-029, to cancel the subscription; fake gateway in tests), `render_signed_pdf` (T-031), `build_cap_table` + `cap_table_csv` (T-003; the CSV is included only when the facts are valid).

## Acceptance criteria

1. `export_zip(user)` returns `({brand slug}-export-{date}.zip, bytes)` (`keelstart-export-2026-11-23.zip` by default, ADR-0041) containing exactly the ADR-0034 files for every company the user belongs to, and nothing from companies they do not belong to (tested with a second customer's data in the same database); never password hashes, session or invite tokens.
2. Export of a company with executed documents includes their signed PDFs; every JSON file is valid and pretty-printed; the zip is reproducible for the same data and date.
3. `delete_account` requires the right password and `confirm == "DELETE"` (else `InvalidCredentialsError` / `InvalidStateError`); cancels the subscription through the billing service immediately.
4. Companies where the user is the only member are deleted with everything in them (cascade); in shared companies the membership is removed, ownership and billing pass to the longest-standing remaining member, executed documents and signature rows stay with `user_id` set to NULL and the typed name and timestamp kept; an audit entry records "member left (account deleted)".
5. Sessions, auth tokens, invites sent by the user and their outbox rows are deleted; the user row is deleted last; the same email can sign up again afterwards.
6. `DeletionReport` lists deleted companies, kept companies (with the new owner) and counts; it is what the API returns.
7. Works on SQLite; the cascade test also runs on PostgreSQL when `LAUNCH_TEST_POSTGRES_URL` is set.

## Feature run (`evidence/T-037/feature_run.py`)

Builds two companies for Alice (one solo, one shared with Bob and fully executed) plus an
unrelated customer; exports Alice's data and prints the zip's file list and sizes; deletes
Alice's account and prints the `DeletionReport`, then shows that the shared company now
belongs to Bob with the signed PDF still downloadable and Alice's signature kept by name,
that the solo company is gone, and that the unrelated customer is untouched.

## Out of scope

HTTP routes (T-039), the settings screens (T-044).
