# ADR-0035: Frontend v2: brand, routes, layouts and feature boundaries

| | |
|---|---|
| **Status** | Accepted; Brand section superseded by ADR-0039, now by [ADR-0041](0041-brand-keelstart-everywhere-customers-look.md) |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor, product owner (product name: open question Q-007) |
| **Tickets** | T-011 (implements the foundation), T-018..T-022, T-036, T-042..T-045 (feature screens), T-023, T-046 |
| **Scope** | `frontend/src/` |

## Context

ADR-0019 fixed tokens, components, the chat-plus-workspace shell and a founder switcher
for an app without accounts. The sellable product adds public marketing and legal pages,
sign-up / login / onboarding, settings (profile, team, billing, privacy), an admin area,
a consistent brand, and trust signals where founders make decisions; the founder
switcher becomes demo-mode only. This ADR **supersedes ADR-0019**. Kept unchanged from
ADR-0019: the token set and contrast rules, the type scale, spacing, radius, shadow and
motion rules, the shared component list, agent identity, the desktop/phone workspace
layout and copy guidelines.

## Decision

### Brand

- Product name comes from `GET /api/config` (`brand_name`, backend `BRAND_NAME`,
  default **"Charterly"** pending Q-007) with the same compiled fallback in
  `src/brand/brand.ts`; nothing else hard-codes the name. Renaming = one env value.
- `src/brand/`: `Logo` (inline SVG mark: a folded-document shape with a check, in
  `primary`, plus the word mark), `BrandName`, favicon set, Open Graph image, the
  tagline "Launch your company with a team of AI agents" and the disclaimer line
  "Not legal advice. We're not a law firm."
- Primary color: deep indigo; accents per agent as in ADR-0019.

### Routes (T-011 owns the router; each page comes from a feature folder)

| Path | Page (named export from) | Layout | Access |
|---|---|---|---|
| `/` | `LandingPage` (`features/marketing`) | Marketing | public |
| `/pricing` | `PricingPage` (`features/marketing`) | Marketing | public |
| `/terms`, `/privacy`, `/disclaimer`, `/security` | `TermsPage`, `PrivacyPage`, `DisclaimerPage`, `SecurityPage` (`features/marketing`) | Marketing | public |
| `/login`, `/signup`, `/forgot-password`, `/reset-password`, `/verify-email` | `LoginPage`, `SignupPage`, `ForgotPasswordPage`, `ResetPasswordPage`, `VerifyEmailPage` (`features/auth`) | Auth (centered card) | public (logged-in users are sent to `/app`) |
| `/invite/:token` | `InvitePage` (`features/auth`) | Auth | public, accept needs login |
| `/app` | `CompaniesPage` (`features/onboarding`) | App | user |
| `/app/onboarding` | `OnboardingPage` (`features/onboarding`): describe your company -> meet your agents -> first chat | App | user |
| `/app/cases/:caseId/:view?` | workspace; `view` in `overview, names, legal, cap-table, website, guide, team, audit` | App (chat + workspace) | member |
| `/app/settings/:section?` | `SettingsPage` (`features/settings`): `profile`, `security`, `billing`, `privacy` | App | user |
| `/app/billing/test-checkout` | `TestCheckoutPage` (`features/settings`), only when payments are fake | App | user |
| `/admin/:section?` | `AdminPage` (`features/admin`): `users`, `companies`, `usage`, `jobs`, `emails`, `system` | App | admin |
| `/design` | component gallery | bare | development builds only |

Logged-out access to `/app/*` redirects to `/login?next=...`; a 401 from any API call
does the same. Unknown routes show a friendly 404 with links home.

### Folder layout and owners

```
frontend/src/
  main.tsx, App.tsx, app/, design/, agents/, api/, lib/, brand/, test/     T-011
  public/theme-init.js (no inline scripts, ADR-0033)                       T-011
  features/chat/  features/overview/                                       T-018
  features/names/ features/guide/                                          T-019
  features/legal/ features/audit/                                          T-020
  features/cap-table/                                                      T-021
  features/website/                                                        T-022
  features/auth/                                                           T-042
  features/onboarding/                                                     T-036
  features/marketing/                                                      T-043
  features/settings/ features/team/                                        T-044
  features/admin/                                                          T-045
```

Workspace views keep ADR-0019's contract: `features/<view>/index.tsx` default-exports
`(props: { caseId: string }) => JSX.Element` (`team` is the `features/team` default
export). Non-workspace folders export the named pages in the table. T-011 ships a
placeholder for every export; the feature ticket replaces its folder. Features import
only from `@/design`, `@/api`, `@/agents`, `@/lib`, `@/brand`, `@/app` and their own folder.

### App shell additions (T-011)

- **Header:** logo, company switcher (the user's companies), progress for the current
  company, help link, theme toggle, account menu (name, plan badge, Settings, Log out).
  The **founder switcher** ("Acting as") renders only when `PublicConfig.demo_mode` is
  true, sends `X-Act-As-Founder`, and shows a "Demo mode" badge.
- **Banners:** "Confirm your email to sign documents" (resend), "Test mode: payments are
  simulated" when payments are fake, "You've reached your plan's AI allowance" (link to billing).
- **Trust signals** (shared `TrustNote` component): security note under sign-up and
  payment buttons; the disclaimer at every legal decision; per-step status chips.
- **Upgrade prompts:** a `PlanGate` component wraps any action whose API call can return
  `plan_required`, showing what the plan unlocks and a button to `/pricing`.

### API client additions (`api/`, T-011)

`types.ts` mirrors ADR-0026/0028/0030/0031/0032 views; `client.ts` has one function per
ADR-0032 endpoint, sends `credentials: "include"` and the `X-CSRF-Token` header (from
`MeView.csrf_token` / the `la_csrf` cookie) on unsafe methods, applies the ADR-0023
timeouts and retries, parses the error envelope into `ApiError{code, message, status,
requestId}`; `hooks.ts` adds `useMe`, `useConfig`, auth mutations, `useMembers`,
`useInvites`, `usePlans`, `useSubscription`, `useCheckout`, `usePortal`, `useJob`
(polls every 1.5 s until finished), `useAdmin*`, `useExport`, `useDeleteAccount`.

### Quality bar (every UI ticket)

As ADR-0019 and the brief: responsive to 390 px with no horizontal page scroll, light
and dark mode, keyboard accessible with visible focus, WCAG AA, loading / empty / error
states on every view (errors offer a recovery action), no layout shift, friendly copy,
no raw JSON or stack traces. Marketing and auth pages are also measured for a
first-load JS budget of 250 KB gzip (route-level code splitting with `React.lazy`).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. One SPA with public, auth, app and admin layouts and folder ownership (chosen) | One build, one design system, parallel feature tickets | Marketing pages are client-rendered |
| B. Separate static marketing site | Best SEO | Second build and design system |
| C. Server-rendered framework (Next.js) | SEO + SSR | Different stack from the approved one |

## Consequences

- Ten feature tickets in wave 4 build screens in parallel against T-011's shell.
- The product name changes in one place once the owner answers Q-007.
