# T-042: Auth screens: sign up, log in, verify email, reset password, accept a co-founder invite

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-039 |
| **ADRs** | [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0033](../docs/adr/0033-security-hardening.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0036](../docs/adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

A visitor creates an account or logs in on calm, trustworthy pages, confirms their email
from the link, recovers a forgotten password, and a co-founder opens an invite link,
signs up or logs in with the invited email and lands in the shared company.

## Owns (only these paths may change)

- `frontend/src/features/auth/`
- `evidence/T-042/`
- `prs/T-042.md`

## Contracts

- **Provides:** `LoginPage`, `SignupPage`, `ForgotPasswordPage`, `ResetPasswordPage`, `VerifyEmailPage`, `InvitePage` (named exports, ADR-0035).
- **Consumes:** `@/design` (`FormField`, `TrustNote`, `Banner`), `@/brand`, `@/api` auth and invite hooks (T-011); endpoints from T-039.

## Acceptance criteria

1. Sign-up: full name, email, password with live strength/policy hints (zod schema mirroring ADR-0026 limits), "I agree to the Terms and Privacy Policy" checkbox linking both pages, security `TrustNote`, submit with loading state; success goes to `/app/onboarding` with the "confirm your email" banner; duplicate email shows the friendly message with links to log in / reset.
2. Log in: email + password, "Forgot password?", friendly generic error, `?next=` honoured (only same-origin paths), already-logged-in users go to `/app`.
3. Verify email: reads `token`, shows success (then continues) or expired-link state with "Resend email" (when logged in).
4. Forgot / reset password: forgot always shows "If an account exists, we sent a link"; reset validates the policy, shows success and sends the user to log in; expired token state.
5. Invite: preview shows company, inviter, masked email and founder name; logged out -> "Sign up" / "Log in" keeping the invite (return URL); logged in with the wrong email -> clear explanation and "Log out and switch"; accept -> lands in `/app/cases/{id}/overview` with a welcome toast.
6. Rate-limit (429) responses show "Too many attempts. Try again in N minutes." without clearing the form.
7. Password fields have show/hide toggles with accessible labels; autocomplete attributes are correct (`email`, `current-password`, `new-password`).
8. Component tests cover validation messages, the generic login error, `next` handling, invite states and 429 handling.
9. **Quality bar:** responsive at 390px with no horizontal page scroll, light and dark mode, keyboard accessible with visible focus, WCAG AA contrast, loading/empty/error states, no layout shift, friendly copy.
10. **Playwright screenshots** in `evidence/T-042/` at 1280px and 390px, light and dark.

## Feature run (`evidence/T-042/feature_run.py`)

With `running_app()` (no seed): signs up a new user through the form, reads the
verification link with `app.read_emails(to=...)` (the run's email drop file) and opens it; logs out and in; uses forgot/reset password and logs
in with the new password; triggers a wrong-password error and the rate-limit message
(limits enabled for this run). With `running_app(seed_stage="names")`: Alice invites a new
co-founder email, the invite link is opened in a fresh context, the co-founder signs up
with that email, accepts and lands in the company. Saves matrices `signup`, `login`,
`reset`, `invite`; checks no horizontal scroll and no raw JSON.

## Out of scope

Onboarding (T-036), settings (T-044), marketing pages (T-043).
