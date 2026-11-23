# T-011: Frontend foundation: design system, themes, app shell with agent-aware chat layout, typed API client, UI-run helper

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0018](../docs/adr/0018-frontend-stack-and-npm-package-set.md), [ADR-0019](../docs/adr/0019-frontend-design-system-and-app-layout.md), [ADR-0020](../docs/adr/0020-ui-recorded-runs-and-demo-seeding.md), [ADR-0017](../docs/adr/0017-services-and-http-api-surface.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

The web app exists and already looks like a trustworthy SaaS product: one set of design
tokens, light and dark themes, every shared component, the app shell (header with
founder switcher and theme toggle, chat panel beside a tabbed workspace, phone layout),
agent identities, and a typed client for the whole API, so five screen tickets can be
built in parallel later.

## Owns (only these paths may change)

- `frontend/`
- `launch_agents/devtools/`
- `tests/test_devtools.py`
- `evidence/T-011/`
- `prs/T-011.md`

## Contracts

- **Provides:** the full `frontend/` project per ADR-0018 (the only ticket that owns `package.json`, the lockfile and config); `src/design` tokens + components, `src/app` shell/routes/header/`FounderSwitcher`/`ThemeToggle`/`ActingFounderContext`/StartScreen, `src/agents` identity map + `AgentAvatar`, `src/api` `types.ts`/`client.ts`/`hooks.ts`/`errors.ts`, `src/lib`, `src/test` helpers, placeholder pages in `src/features/{chat,overview,names,guide,legal,audit,cap-table,website}/index.tsx`, the `/design` gallery (ADR-0019); `launch_agents/devtools/ui_run.py` (ADR-0020).
- **Consumes:** the API contract in ADR-0017 (types only; the case routes arrive in T-016/T-017), T-001's `create_app` skeleton (health + static serving).

## Acceptance criteria

1. `npm ci`, `npm run build` and `npm test` pass; `package.json` lists exactly the ADR-0018 packages (a vitest test reads `package.json` and compares names).
2. Tokens: every ADR-0019 color token exists for light and dark; a vitest test parses `tokens.css` and checks the AA ratios for text/background pairs, badge pairs and agent accents on surfaces; Tailwind classes use tokens only (no hex colors in components).
3. Every shared component in ADR-0019 exists, is shown in `/design` in all variants and states (incl. loading, disabled, error), has a visible `focus-visible` ring, and has at least one behaviour test (e.g. Dialog traps focus and closes on Escape, Toast announces politely, Table stacks below 640px, `IconButton` requires a label at type level).
4. Shell: header, chat panel slot, workspace tabs for the seven views with the 6-step progress strip, routes per ADR-0019, phone layout with the Chat/Workspace switch; keyboard: tab order is logical, skip-to-content link, tabs operable by arrow keys.
5. Theme: system default, toggle persisted under `launch.theme`, no flash of the wrong theme (inline script), and `prefers-reduced-motion` respected.
6. Founder switcher: lists the case's founders from `useCase`, persists per case, shows "Acting as {name}" and the "no real sign-in in this release" note; empty when no founders yet.
7. API client: one function per ADR-0017 endpoint with typed request/response; the error envelope becomes `ApiError` with the friendly message; network failure becomes a friendly `ApiError`; tests mock `fetch`.
8. Every view placeholder shows proper loading (skeleton), empty and error states; an unknown case shows "We couldn't find this company" with a way back, never raw JSON.
9. `ui_run.py` implements `build_frontend`, `running_app`, `capture_matrix`, `assert_no_horizontal_scroll`, `assert_no_raw_json` per ADR-0020; `tests/test_devtools.py` tests the parts that need no browser (free-port selection, env composition, screenshot file naming).
10. **Quality bar:** responsive at 390px with no horizontal page scroll, light and dark mode, keyboard accessible with visible focus, WCAG AA contrast, loading/empty/error states, no layout shift (skeletons sized like content), friendly copy.
11. **Playwright screenshots** (ADR-0005/0020) of `/design`, `/` and `/cases/unknown/overview` at 1280px and 390px in light and dark are in `evidence/T-011/`.

## Feature run (`evidence/T-011/feature_run.py`)

Builds the frontend, starts the app with `running_app()` (no seed), and with Playwright:
opens `/design` and asserts each component section is visible; toggles the theme and
asserts the `dark` class and persistence after reload; tabs through the header and
asserts a visible focus ring; opens `/` (start screen with its loading then error/empty
state because the case API is not there yet) and `/cases/unknown/overview` (friendly
not-found state, workspace tabs visible); runs `assert_no_horizontal_scroll` at 390px and
`assert_no_raw_json`; saves the screenshot matrix for all three pages.

## Out of scope

Real feature screens (T-018–T-022), backend routes (T-016, T-017).
