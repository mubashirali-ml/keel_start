# T-011: Frontend foundation: brand, design system, themes, app shell and layouts, typed API client with auth, UI-run helper

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0041](../docs/adr/0041-brand-keelstart-everywhere-customers-look.md), [ADR-0038](../docs/adr/0038-plans-v2-free-launch-team-and-plan-settings.md), [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md), [ADR-0025](../docs/adr/0025-dependency-set-v2-python-and-npm.md), [ADR-0036](../docs/adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0033](../docs/adr/0033-security-hardening.md), [ADR-0023](../docs/adr/0023-reliability-timeouts-retries-and-failure-states.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0019](../docs/adr/0019-frontend-design-system-and-app-layout.md) (tokens and components, kept by ADR-0035), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

The web app exists and already looks like a trustworthy SaaS product: the brand (name,
logo mark, colors), one set of design tokens, light and dark themes, every shared
component, the public, auth, app and admin layouts with every route and a placeholder
per page, the chat-plus-workspace shell, agent identities, and a typed API client with
sessions, CSRF and friendly errors, so nine screen tickets can be built in parallel later.

## Owns (only these paths may change)

- `frontend/`
- `launch_agents/devtools/`
- `tests/test_devtools.py`
- `evidence/T-011/`
- `prs/T-011.md`

## Contracts

- **Provides:** the full `frontend/` project (the only ticket that owns `package.json`, the lockfile and config, with exactly the ADR-0025 npm set); `src/brand` per ADR-0041 (`Logo`: the ADR-0041 sailboat mark (triangular sail, shallow hull, short keel fin, flat inline SVG in `primary`, with a `currentColor` variant) beside the "Keelstart" word mark, `BrandName`, `brand.ts` with the compiled fallback "Keelstart", favicon from the same mark, OG image (mark, word mark and tagline), tagline as one constant (default pending Q-010), disclaimer line, `pageTitle(page)` -> `{page} · Keelstart`); `src/design` tokens + every ADR-0019 component plus `TrustNote`, `PlanGate`, `Banner`, `FormField` (react-hook-form + zod helpers), `Switch`, `RadioGroup`, `Popover`; `src/app` router with every ADR-0035 route, `MarketingLayout`, `AuthLayout`, `AppShell` (header with company switcher, account menu, plan badge, demo-only `FounderSwitcher`, theme toggle), `RequireAuth`, `RequireAdmin`, the email-verification / test-mode / allowance banners, `ActingFounderContext` (demo mode only), 404 page; `src/agents`; `src/api` (`types.ts` mirroring ADR-0026/0028/0030/0031/0032, `client.ts` one function per ADR-0032 endpoint with `credentials: "include"`, CSRF header, timeouts and retries, `errors.ts` `ApiError{code, message, status, requestId}`, `hooks.ts` incl. `useMe`, `useConfig`, `useJob`, `useSubscription` returning `BillingOverview` and `useChangePlan` (ADR-0038)); the help menu's "Contact support" `mailto:` built from `PublicConfig.support_email` with the `[{Plan name}]` subject prefix and the last error's request id (ADR-0038); `src/lib`; `src/test`; placeholder exports for every feature folder of ADR-0035; `public/theme-init.js`; the `/design` gallery; `launch_agents/devtools/ui_run.py` (ADR-0036: `running_app`, `login`, `build_frontend`, `capture_matrix`, `assert_no_horizontal_scroll`, `assert_no_raw_json`, `DEMO_TODAY`, `DEMO_PASSWORD`, `RunningApp`).
- **Consumes:** the API contract in ADR-0032 (types only; routes arrive in wave 3), T-001's `create_app` skeleton (health + static serving), `GET /api/config` shape (falls back to compiled defaults while the route does not exist).

## Acceptance criteria

1. `npm ci`, `npm run build` and `npm test` pass; the logo mark renders legibly at 16 px (favicon) and 32 px and is shown in `/design` in light, dark and one-colour variants; a vitest test finds the literal "Keelstart" in `src/` only inside `src/brand/` (test files excepted; ADR-0041); a vitest test compares `package.json` dependency names with the ADR-0025 list exactly.
2. Tokens: every color token for light and dark, with `primary` a deep navy blue (ADR-0041); a vitest test parses `tokens.css` and checks AA ratios (text/background, badges, agent accents, brand primary on surfaces); components use tokens only (no hex colors).
3. Every shared component exists, is shown in `/design` in all variants and states, has a visible `focus-visible` ring and at least one behaviour test (Dialog focus trap + Escape, Toast polite announcement, Table stacks below 640px, `IconButton` label required by type, `FormField` shows zod errors accessibly, `PlanGate` renders the upgrade prompt for an `ApiError` with code `plan_required`, naming the plan from `details.required_plan` ("Available on Launch and Team" / "Upgrade to Team for more companies") and falling back to Launch).
4. Routes: every ADR-0035 path renders its placeholder inside the right layout; `/app/*` without a session redirects to `/login?next=...`; a 401 from any call redirects the same way; `/admin` for a non-admin shows a friendly "not available" page; unknown paths show the 404 page.
5. App shell: header (logo, company switcher, progress, account menu with plan badge and Log out, theme toggle), chat panel slot, workspace tabs for the eight views with the 6-step progress strip, phone layout with the Chat/Workspace switch; skip-to-content link; logical tab order; tabs operable by arrow keys. The founder switcher renders **only** when `config.demo_mode` is true, shows a "Demo mode" badge and sends `X-Act-As-Founder`; tests cover both modes.
6. Theme: system default, toggle persisted under `launch.theme`, no flash of the wrong theme using the static `public/theme-init.js` (no inline scripts anywhere: a test scans `index.html` and the build output), `prefers-reduced-motion` respected.
7. API client: typed function per ADR-0032 endpoint; unsafe methods send `X-CSRF-Token` from the `la_csrf` cookie / `MeView.csrf_token`; error envelope -> `ApiError` with friendly message and request id; network failure and timeouts (chat 100 s, others 20 s) -> friendly `ApiError`; GET retried twice on network errors, mutations never; tests mock `fetch`.
8. Every placeholder shows loading (skeleton), empty and error states; an unknown company shows "We couldn't find this company" with a way back, never raw JSON.
9. `ui_run.py` per ADR-0036: `running_app` composes the env (`APP_ENV=test`, fakes, `DEMO_MODE`, `RATE_LIMITS_ENABLED=0`, `EMAIL_DROP_FILE`, migrated temp SQLite) and `RunningApp.read_emails` parses the drop file, seeds before start, waits for `/api/ready` (falls back to `/api/health` while readiness is not implemented); `login` uses the real login form; `tests/test_devtools.py` covers free-port selection, env composition and screenshot naming without a browser.
10. **Quality bar:** responsive at 390px with no horizontal page scroll, light and dark mode, keyboard accessible with visible focus, WCAG AA contrast, loading/empty/error states, no layout shift, friendly copy; marketing/auth route chunks are code-split.
11. **Playwright screenshots** (ADR-0005/0036) of `/design`, `/` (marketing placeholder with brand header and footer), `/login` (auth layout) and `/app/cases/unknown/overview` (logged-out redirect to login) at 1280px and 390px in light and dark are in `evidence/T-011/`.

## Feature run (`evidence/T-011/feature_run.py`)

Builds the frontend, starts the app with `running_app()` (no seed), and with Playwright:
opens `/design` and asserts each component section; toggles the theme and asserts the
`dark` class persists after reload; tabs through the header and asserts a visible focus
ring; opens `/` and asserts the logo, the brand name "Keelstart", the page title and the disclaimer line; opens
`/app/cases/unknown/overview` and asserts the redirect to `/login?next=...`; checks that
the page has no inline `<script>` without `src`; runs `assert_no_horizontal_scroll` at
390px and `assert_no_raw_json`; saves the screenshot matrices.

## Out of scope

Real screens (T-018..T-022, T-042..T-045), backend routes (wave 3), demo seeding (T-016).
