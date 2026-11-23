# T-026: Accounts: sign-up, login, sessions, email verification and password reset

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md), [ADR-0029](../docs/adr/0029-transactional-email-notifications-and-83b-reminders.md), [ADR-0033](../docs/adr/0033-security-hardening.md), [ADR-0025](../docs/adr/0025-dependency-set-v2-python-and-npm.md) |
| **Status** | todo |

## Goal

Founders can create an account with email and password, log in and out, stay signed in
with an expiring, revocable session, confirm their email, and reset a forgotten password
by email, with passwords hashed using argon2id and no way to tell from the answers
whether an email is registered.

## Owns (only these paths may change)

- `launch_agents/accounts/`
- `launch_agents/persistence/accounts.py`
- `tests/test_auth.py`
- `tests/test_accounts_repository.py`
- `evidence/T-026/`
- `prs/T-026.md`

## Contracts

- **Provides:** `hash_password`, `verify_password`, `needs_rehash`, `check_password_policy`, `SessionToken`, `AuthService` (every method of ADR-0026); `AccountsRepository` (ADR-0027) incl. `SessionRecord`.
- **Consumes:** `tables.py` (T-001), `User`, `RequestContext`, errors (T-001), `Mailer` + `RecordingMailer` and `EmailTemplate.VERIFY_EMAIL` / `PASSWORD_RESET` (T-001 port; the real templates arrive in T-028), `Settings` (session days, base URL), packages `argon2-cffi`, `email-validator`.

## Acceptance criteria

1. `signup` normalises and validates the email, applies the password policy (10–128 chars, not the email, not in the bundled 1,000 common passwords), stores an argon2id hash, creates a session, and sends `verify_email` with a link `{APP_BASE_URL}/verify-email?token=...`; a duplicate email -> `ConflictError` with "An account with this email already exists. Log in or reset your password."
2. `login`: right password -> new session token (rotation: every login creates a new one); wrong password or unknown email -> the same `InvalidCredentialsError` ("Email or password is incorrect"); hash rehashed when `needs_rehash`.
3. Sessions: only the SHA-256 of the token is stored; `resolve_session` returns the user, extends idle expiry (7 days) but never past the absolute 30 days, and returns None for unknown, expired or revoked tokens; `logout` revokes.
4. Verification: tokens are random, stored hashed, single use, 48 h; `verify_email` sets `email_verified_at`; reuse or expiry -> `TokenInvalidError` ("This link has expired. Request a new one.").
5. Reset: `request_password_reset` sends `password_reset` (1 h token) for a known email and does nothing visible for an unknown one; `reset_password` changes the hash and revokes every session; `change_password` checks the current password and revokes every other session.
6. Repository: every `AccountsRepository` method on a real SQLite file; unique email enforced; `list_users` with query and paging for the admin area.
7. No password, hash or raw token appears in any log line or exception message (tested with `caplog`).
8. Tests use `RecordingMailer` and an injected clock; no network.

## Feature run (`evidence/T-026/feature_run.py`)

On a temp SQLite database with `RecordingMailer`: signs up Alice (prints the verification
email's template and link, token masked), verifies her email, logs out and in again (two
different session hashes), tries a wrong password and an unknown email (prints the same
friendly error), resolves her session after 6 days (extended) and after 31 days
(expired), requests a reset for her and for an unknown email (one email sent), resets the
password and shows that the old session no longer resolves.

## Out of scope

HTTP routes and cookies (T-039), team and invites (T-027), email templates (T-028), rate limits (T-032).
