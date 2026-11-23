# T-044: Settings and team: profile, security, billing and plan, data export and deletion, co-founders and invites

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-039, T-040 |
| **ADRs** | [ADR-0038](../docs/adr/0038-plans-v2-free-launch-team-and-plan-settings.md), [ADR-0042](../docs/adr/0042-support-wording-no-promised-reply-times.md), [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

A customer manages everything about their account in one calm place: name and password,
their plan (upgrade from Free through Stripe Checkout, switch between Launch and Team or
monthly and yearly in place, invoices and cancellation in the Stripe portal), what they
have used of the plan, downloading all their data or deleting their account; and an owner invites
co-founders and sees who has joined each company.

## Owns (only these paths may change)

- `frontend/src/features/settings/`
- `frontend/src/features/team/`
- `evidence/T-044/`
- `prs/T-044.md`

## Contracts

- **Provides:** `SettingsPage` (sections `profile`, `security`, `billing`, `privacy`) and `TestCheckoutPage` (named exports), the Team workspace view (default export of `features/team`) (ADR-0035).
- **Consumes:** `@/design`, `@/api` (`useMe`, account mutations, `usePlans`, `useSubscription` (returns `BillingOverview`, ADR-0038), `useCheckout`, `useChangePlan`, `usePortal`, `useExport`, `useDeleteAccount`, `useMembers`, `useInvites`, invite mutations, `useCase`) (T-011); endpoints from T-039, T-040.

## Acceptance criteria

1. Profile: edit full name (validated), email shown read-only with verification status and "Resend email".
2. Security: change password (current + new with policy hints); success says other devices were signed out.
3. Billing: current plan with its support label from the API ("Email support" or "Priority support", no reply time, ADR-0042), status (active / canceling on {date} / past due with a calm warning), interval and renewal date; usage meters for AI messages this month (with reset date) and companies against the plan limits (warning tone above 80 %); on Free, Launch and Team cards to upgrade (Checkout redirect, monthly/yearly); when paying, "Switch plan" offering the other paid plan and the other interval in a `ConfirmDialog` that says the change is prorated by Stripe and takes effect now, then shows the new plan (`useChangePlan`); "Manage billing, invoices and cancellation" (portal redirect) for paid, with a note that going back to Free is a cancellation; `?checkout=success` shows a success banner after the webhook has updated the plan (polls `useSubscription` briefly; explains if it takes longer); test-mode badge when payments are simulated.
4. Test checkout page (fake payments only): looks like a simple checkout summary labelled "Test mode", "Pay (test)" completes via the API and returns to billing; not reachable when payments are real (redirects to billing).
5. Privacy: "Download all my data" (zip download) with a description of the contents; "Delete account" in a `ConfirmDialog` that explains what happens to shared and solo companies, requires the password and typing DELETE, then logs out to the landing page with a confirmation.
6. Team view (per company): members with role and linked founder; founders from the facts without an account appear with an "Invite" button (email prefilled); pending invites with resend/revoke; members without `MANAGE_TEAM` see a read-only list; "Leave company" for members; the last owner cannot leave (explained).
7. Component tests cover each section's states (Free, Launch, Team, canceling, past due), the usage meter thresholds, the switch-plan dialog, the delete confirmation, the checkout-success polling and the team permissions.
8. **Quality bar:** responsive at 390px with no horizontal page scroll, light and dark mode, keyboard accessible with visible focus, WCAG AA contrast, loading/empty/error states, no layout shift, friendly copy.
9. **Playwright screenshots** in `evidence/T-044/` at 1280px and 390px, light and dark.

## Feature run (`evidence/T-044/feature_run.py`)

With `running_app(seed_stage="new", plan="free")`, Alice logged in: changes her name;
upgrades to Launch through the test checkout and asserts the plan badge, the usage meters
and success banner; switches to Team through the confirm dialog and asserts the Team badge
and limits; opens the portal action (asserts the redirect URL from the fake gateway); with
`seed_stage="facts"` opens Team, asserts Bob as a member, invites a third email and
revokes it; downloads her data (zip checked); deletes the account of a fresh user and
asserts the landing page confirmation. Saves matrices `settings-billing`,
`settings-privacy`, `team`; checks no horizontal scroll and no raw JSON.

## Out of scope

Pricing page (T-043), admin (T-045), sign-up (T-042).
