# T-039: HTTP API: sign-up, login, sessions, account settings, data export and deletion, team and invites

| | |
|---|---|
| **Wave** | 3 |
| **Depends on** | T-026, T-027, T-032, T-037 |
| **ADRs** | [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0033](../docs/adr/0033-security-hardening.md), [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md) |
| **Status** | todo |

## Goal

Over HTTP, a visitor can sign up, confirm their email, log in and out with a secure
session cookie, reset a forgotten password, update their profile and password, export or
delete their data, and company owners can invite co-founders who accept with their own
account, all rate limited and protected against cross-site requests.

## Owns (only these paths may change)

- `launch_agents/api/routes/auth.py`
- `launch_agents/api/routes/account.py`
- `launch_agents/api/routes/team.py`
- `tests/test_api_auth.py`
- `tests/test_api_account.py`
- `tests/test_api_team.py`
- `evidence/T-039/`
- `prs/T-039.md`

## Contracts

- **Provides:** the T-039 rows of the ADR-0032 table as `router = APIRouter()` in each file, with request bodies (`extra="forbid"`, ADR-0033 limits).
- **Consumes:** `AuthService` (T-026), `TeamService` (T-027), `PrivacyService` (T-037), `RateLimiter` + `issue_csrf_token` (T-032), `require_user` / `require_case` / `rate_limit` / `set_session_cookie` / `clear_session_cookie` (T-016 `api/deps.py`, same wave: tests use a minimal app with equivalent dependencies built from the wave-1/2 services), `MeView`, `MemberView`, `InvitePreview` (T-001).

## Acceptance criteria

1. Sign-up (`accept_terms` must be true) -> 201 `MeView`, `Set-Cookie: la_session` (HttpOnly, SameSite=Lax, Secure in production) and `la_csrf`; login rotates the session; logout clears both cookies and revokes the session; `GET /api/auth/me` -> `MeView` or 401.
2. Verify email, resend verification, forgot password (always 204), reset password (revokes sessions; the response sets no session) behave per T-026 with friendly envelopes for bad tokens.
3. Rate limits per ADR-0033 classes (`auth`, `email`, `invite`) return 429 with `Retry-After`; tests enable the limiter.
4. `PATCH /api/account`, `POST /api/account/password` (revokes other sessions), `GET /api/account/export` (zip download from `PrivacyService`), `DELETE /api/account` (password + `DELETE`, returns the deletion report summary, clears cookies).
5. Team: members list (`VIEW`), invites list/create/revoke (`MANAGE_TEAM`; 403 for a member), remove member / leave; `GET /api/invites/{token}` public preview; `POST /api/invites/{token}/accept` requires login with the invited email (403 otherwise) and returns the company id.
6. Responses never include password hashes, raw tokens (except the CSRF token in `MeView`), or another user's email in full outside their company's member list.
7. Every unsafe route requires the CSRF header (checked by T-016's route-contract test once merged; asserted here too).

## Feature run (`evidence/T-039/feature_run.py`)

Over `TestClient` with fakes and a recording mailer: Alice signs up (prints cookies'
attributes and the verification email link), verifies, logs out and in; a wrong password
six times shows the 429; Alice creates a company through the services, invites Bob (prints
the invite email), Bob signs up with another email and is refused, then with the invited
email and accepts; prints the member list; Alice exports her data (zip file list) and
finally deletes her account (report printed; Bob now owns the company).

## Out of scope

The app and dependencies (T-016), the screens (T-042, T-044).
