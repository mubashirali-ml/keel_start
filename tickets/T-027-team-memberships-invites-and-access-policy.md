# T-027: Team: memberships, co-founder invites and the access policy for every company

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md), [ADR-0029](../docs/adr/0029-transactional-email-notifications-and-83b-reminders.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md) |
| **Status** | todo |

## Goal

Each person sees only the companies they belong to and can act only as themselves: the
creator owns the company, invites co-founders by an email link, each co-founder joins
with their own account linked to their founder in the case, and one access check decides
for every request what the caller may do (with "act as founder" only in demo mode).

## Owns (only these paths may change)

- `launch_agents/team/`
- `launch_agents/access/`
- `launch_agents/persistence/team.py`
- `tests/test_team.py`
- `tests/test_access_policy.py`
- `evidence/T-027/`
- `prs/T-027.md`

## Contracts

- **Provides:** `TeamService` (every method of ADR-0026), `TeamRepository` (ADR-0027), `ROLE_PERMISSIONS`, `authorize_case(ctx, case_id, permission, *, team, repo, entitlements)` (ADR-0026).
- **Consumes:** `tables.py`, `Membership`, `Invite`, `Permission`, `RequestContext`, `Actor`, `CaseAccess`, `MemberView`, `InvitePreview`, errors (T-001); `Repository` and `AccountsRepository` **through their T-001 stubs only in signatures**: tests use small in-file fakes for the case repository and account lookups, plus `RecordingMailer` and `StaticEntitlements`.

## Acceptance criteria

1. `add_owner` creates the OWNER membership; `members` returns `MemberView`s with founder names from the case facts.
2. `invite` (MANAGE_TEAM only): creates an invite with a random token stored hashed (7 days), sends `invite_cofounder` with `{APP_BASE_URL}/invite/<token>`; inviting a founder prefills that founder's email; inviting an existing member or an email with a pending invite -> `ConflictError`; `revoke_invite` works; a member without MANAGE_TEAM -> `ForbiddenError`.
3. `preview_invite` returns company, inviter, masked email, founder name and `expired`; `accept_invite` requires the logged-in user's email to equal the invite email (else `ForbiddenError` "This invite was sent to a***@example.com. Log in with that email."), creates the MEMBER membership linked to the invite's founder, marks the invite accepted; second use -> `TokenInvalidError`.
4. A founder links to at most one user per company; `link_founder` enforces it; the last owner cannot leave or be removed.
5. `authorize_case` follows ADR-0026 in order: no user -> `AuthRequiredError`; missing company **or non-member** -> `NotFoundError` with the same message; missing permission -> `ForbiddenError`; `SIGN`/`EDIT_DOCUMENTS` without a linked founder -> `ForbiddenError` explaining the account is not linked to a founder; entitlements come from the company's billing user.
6. Demo mode: with `ctx.demo_mode` and `act_as_founder_id`, the actor becomes the member linked to that founder with `acted_by_user_id` set; without demo mode the header value is ignored (and a warning logged); acting as a founder with no linked member -> `ForbiddenError`.
7. `ROLE_PERMISSIONS`: OWNER has all; MEMBER all but `MANAGE_TEAM` and `DELETE_COMPANY` (table test).
8. Repository methods tested on real SQLite, including the unique founder-per-company constraint.

## Feature run (`evidence/T-027/feature_run.py`)

On a temp SQLite database with fakes: Alice owns a company with founders Alice (f1) and
Bob (f2); she invites Bob (prints the invite email and masked preview); Carol tries to
accept Bob's invite (rejected), Bob accepts (linked to f2); prints the member list; runs
`authorize_case` for Alice, Bob, Carol (not found) and an anonymous caller for several
permissions and prints the results table; shows demo-mode act-as on and off.

## Out of scope

HTTP routes (T-039), team screen (T-044), linking the owner by email when facts lock (T-014), sign-up (T-026).
