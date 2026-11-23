# T-043: Public pages: landing, pricing, Terms of Service, Privacy Policy, disclaimer and security

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-040 |
| **ADRs** | [ADR-0042](../docs/adr/0042-support-wording-no-promised-reply-times.md), [ADR-0038](../docs/adr/0038-plans-v2-free-launch-team-and-plan-settings.md), [ADR-0041](../docs/adr/0041-brand-keelstart-everywhere-customers-look.md), [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0031](../docs/adr/0031-electronic-signatures-and-signed-pdfs.md), [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md), [ADR-0033](../docs/adr/0033-security-hardening.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

A founder who finds Keelstart understands in one minute what the agents do, sees
honest pricing across three plans (Free, Launch, Team), can read clear Terms, Privacy Policy and the "not legal advice; we're not
a law firm" disclaimer, and starts a plan or a free account with confidence.

## Owns (only these paths may change)

- `frontend/src/features/marketing/`
- `evidence/T-043/`
- `prs/T-043.md`

## Contracts

- **Provides:** `LandingPage`, `PricingPage`, `TermsPage`, `PrivacyPage`, `DisclaimerPage`, `SecurityPage` (named exports, ADR-0035).
- **Consumes:** `@/design`, `@/brand`, `@/agents`, `@/api` (`usePlans`, `useConfig`, `useMe`, `useCheckout`) (T-011); endpoints from T-040 (plans, checkout).

## Acceptance criteria

1. Landing: hero (the Keelstart word mark from `@/brand`, tagline "Launch your company with a team of AI agents", primary "Start free" and secondary "See pricing"), "Meet your agents" section with each agent's identity and the tangible output it produces (documents, name cards with live domain checks, cap table + Excel, e-signatures, website with QA, registration checklist), a three-step "how it works", trust strip (e-signatures with a full record, data export and deletion anytime, admins never read your documents, not a law firm), a pricing teaser with the three plan names and monthly prices from the API, FAQ (incl. "What counts as an AI message?" and "Do co-founders pay?"), footer with legal links, the disclaimer and the ADR-0041 footer line with `[COMPANY LEGAL NAME]`.
2. Pricing: three plan cards from `/api/billing/plans` in `rank` order (name, tagline, price, highlights, support label), Launch marked "Most popular"; a monthly/yearly `RadioGroup` showing yearly as the per-month equivalent plus "2 months free" (computed from the API amounts), hidden when `yearly_enabled` is false; "Start free" -> sign-up; "Choose Launch" / "Choose Team" -> sign-up when logged out (then returns to the same choice), checkout when logged in on Free (`useCheckout` -> redirect), "Switch to {plan}" leading to billing settings when already paying, "Current plan" on the user's plan; a "Test mode: payments are simulated" badge when `payments_test_mode`; a comparison table with rows for companies, AI messages per month, every feature (documents, e-signatures, signed PDF/Word, publishing, cap table, name checks, checklist, 83(b) reminders), co-founders free, and support (the API's `support_label`: "Email support", "Email support", "Priority support", ADR-0042); the AI-message footnote from ADR-0038; no reply time is promised anywhere (ADR-0042): the FAQ may say "Team requests are handled first" but gives no time; nothing hard-codes prices, limits or the brand name.
3. Terms, Privacy, Disclaimer, Security pages: complete, readable drafts in plain English covering the ADR points (service description; not a law firm / not legal advice; the app does not file with the state or buy domains; electronic signatures under ESIGN/UETA with the consent text; billing, renewals and cancellation via the portal; acceptable use; data we store and never store (no SSNs or tax IDs), subprocessors by category (hosting, email, payments, AI provider), retention, export and deletion, admins see metadata only; security measures in plain words); each page shows "Last updated" and a visible "Draft: have your lawyer review before launch" note controlled by one constant, and placeholders `[COMPANY LEGAL NAME]`, `[CONTACT EMAIL]`, `[GOVERNING LAW STATE]` for the owner to fill.
4. SEO basics: per-page `<title>` in the ADR-0041 form (`Pricing · Keelstart`) and meta description via `document.title`/a head helper, Open Graph image from `@/brand`, semantic headings.
5. Performance: marketing routes load without the app bundle (code-split), first-load JS within the ADR-0035 budget (asserted in the feature run from the network log).
6. Component tests cover rendering three plans from API data (and two when the API returns two), interval switching and the hidden toggle when yearly is disabled, the logged-out / Free / paying / current-plan CTAs, the comparison table values, and the test-mode badge.
7. **Quality bar:** responsive at 390px with no horizontal page scroll, light and dark mode, keyboard accessible with visible focus, WCAG AA contrast, loading/empty/error states (pricing when the API fails shows a friendly retry), no layout shift, friendly copy.
8. **Playwright screenshots** in `evidence/T-043/` at 1280px and 390px, light and dark.
9. No-promise check (ADR-0042): a component test renders the pricing page, the FAQ and the Terms page and finds none of the ADR-0042 reply-time phrases ("reply within", "respond within", "response time", "business day", "same day", "answered first", case-insensitive); the Terms draft says support is by email on a reasonable-efforts basis, Team requests are handled first, and there is no service-level commitment.

## Feature run (`evidence/T-043/feature_run.py`)

With `running_app()`: opens `/` and asserts the agents section and legal links; opens
`/pricing`, asserts three cards ($29 and $79 monthly; the yearly equivalents after switching)
and the test-mode badge, the support row ("Email support" / "Email support" / "Priority support") with no reply time on the page, and the page title "Pricing · Keelstart"; clicks "Choose Launch" logged out (lands on sign-up with return), then with
`seed_stage="account", plan="free"` logged in as Alice clicks it again and asserts the
redirect to the in-app test checkout; with `plan="launch"` asserts "Current plan" on
Launch and "Switch to Team"; opens each legal page and asserts its headings and
the draft note; prints the first-load JS size of `/`. Saves matrices `landing`,
`pricing`, `terms`, `privacy`; checks no horizontal scroll and no raw JSON.

## Out of scope

The test checkout page and billing settings (T-044), sign-up (T-042).
