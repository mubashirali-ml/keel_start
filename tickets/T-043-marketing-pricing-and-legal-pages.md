# T-043: Public pages: landing, pricing, Terms of Service, Privacy Policy, disclaimer and security

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-040 |
| **ADRs** | [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0031](../docs/adr/0031-electronic-signatures-and-signed-pdfs.md), [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md), [ADR-0033](../docs/adr/0033-security-hardening.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

A founder who finds the product understands in one minute what the agents do, sees
honest pricing, can read clear Terms, Privacy Policy and the "not legal advice; we're not
a law firm" disclaimer, and starts a plan or a free account with confidence.

## Owns (only these paths may change)

- `frontend/src/features/marketing/`
- `evidence/T-043/`
- `prs/T-043.md`

## Contracts

- **Provides:** `LandingPage`, `PricingPage`, `TermsPage`, `PrivacyPage`, `DisclaimerPage`, `SecurityPage` (named exports, ADR-0035).
- **Consumes:** `@/design`, `@/brand`, `@/agents`, `@/api` (`usePlans`, `useConfig`, `useMe`, `useCheckout`) (T-011); endpoints from T-040 (plans, checkout).

## Acceptance criteria

1. Landing: hero (brand, tagline, primary "Start free" and secondary "See pricing"), "Meet your agents" section with each agent's identity and the tangible output it produces (documents, name cards with live domain checks, cap table + Excel, e-signatures, website with QA, registration checklist), a three-step "how it works", trust strip (e-signatures with a full record, data export and deletion anytime, admins never read your documents, not a law firm), FAQ, footer with legal links and the disclaimer.
2. Pricing: plan cards from `/api/billing/plans` (names, prices, monthly/yearly `RadioGroup` with the yearly saving, highlights); "Start free" -> sign-up; "Choose Launch" -> sign-up when logged out (then returns), checkout when logged in (`useCheckout` -> redirect); a "Test mode: payments are simulated" badge when `payments_test_mode`; a comparison table; nothing hard-codes prices.
3. Terms, Privacy, Disclaimer, Security pages: complete, readable drafts in plain English covering the ADR points (service description; not a law firm / not legal advice; the app does not file with the state or buy domains; electronic signatures under ESIGN/UETA with the consent text; billing, renewals and cancellation via the portal; acceptable use; data we store and never store (no SSNs or tax IDs), subprocessors by category (hosting, email, payments, AI provider), retention, export and deletion, admins see metadata only; security measures in plain words); each page shows "Last updated" and a visible "Draft: have your lawyer review before launch" note controlled by one constant, and placeholders `[COMPANY LEGAL NAME]`, `[CONTACT EMAIL]`, `[GOVERNING LAW STATE]` for the owner to fill.
4. SEO basics: per-page `<title>` and meta description via `document.title`/a head helper, Open Graph image from `@/brand`, semantic headings.
5. Performance: marketing routes load without the app bundle (code-split), first-load JS within the ADR-0035 budget (asserted in the feature run from the network log).
6. Component tests cover plan rendering from API data, interval switching, the logged-in vs logged-out CTA, and the test-mode badge.
7. **Quality bar:** responsive at 390px with no horizontal page scroll, light and dark mode, keyboard accessible with visible focus, WCAG AA contrast, loading/empty/error states (pricing when the API fails shows a friendly retry), no layout shift, friendly copy.
8. **Playwright screenshots** in `evidence/T-043/` at 1280px and 390px, light and dark.

## Feature run (`evidence/T-043/feature_run.py`)

With `running_app()`: opens `/` and asserts the agents section and legal links; opens
`/pricing`, switches monthly/yearly and asserts prices from the API and the test-mode
badge; clicks "Choose Launch" logged out (lands on sign-up with return), then with
`seed_stage="account", plan="free"` logged in as Alice clicks it again and asserts the
redirect to the in-app test checkout; opens each legal page and asserts its headings and
the draft note; prints the first-load JS size of `/`. Saves matrices `landing`,
`pricing`, `terms`, `privacy`; checks no horizontal scroll and no raw JSON.

## Out of scope

The test checkout page and billing settings (T-044), sign-up (T-042).
