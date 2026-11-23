# ADR-0018: Frontend stack and the approved npm package set

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-011 (creates `frontend/`, the only owner of `package.json` and config), T-018..T-022 (consume) |
| **Scope** | `frontend/package.json`, `frontend/package-lock.json`, frontend config files |

## Context

The brief requires a polished React + TypeScript + Vite + Tailwind app. ADR-0005 makes
npm dependencies an architecture decision and lets only one ticket per wave own
`frontend/package.json` and config. Feature tickets (wave 4) must find every primitive
they need already installed.

## Decision

### Packages (the complete allowed set; versions are the minimum line, the lockfile pins)

| Purpose | Package | Version |
|---|---|---|
| UI runtime | `react`, `react-dom` | `^18.3.1` |
| Routing | `react-router-dom` | `^6.28.0` |
| Server state | `@tanstack/react-query` | `^5.59.0` |
| Accessible primitives | `@radix-ui/react-dialog` `^1.1.2`, `@radix-ui/react-tabs` `^1.1.1`, `@radix-ui/react-dropdown-menu` `^2.1.2`, `@radix-ui/react-select` `^2.1.2`, `@radix-ui/react-tooltip` `^1.1.3`, `@radix-ui/react-toast` `^1.2.2`, `@radix-ui/react-checkbox` `^1.1.2`, `@radix-ui/react-progress` `^1.1.0`, `@radix-ui/react-avatar` `^1.1.1`, `@radix-ui/react-scroll-area` `^1.2.0`, `@radix-ui/react-slot` `^1.1.0` | as listed |
| Icons | `lucide-react` | `^0.454.0` |
| Charts | `recharts` | `^2.13.0` |
| Markdown (chat + documents) | `react-markdown` | `^9.0.1` |
| Class helpers | `clsx` `^2.1.1`, `tailwind-merge` `^2.5.4`, `class-variance-authority` `^0.7.0` | |
| Font (self-hosted, no CDN) | `@fontsource-variable/inter` | `^5.1.0` |
| Build (dev) | `vite` `^5.4.10`, `@vitejs/plugin-react` `^4.3.3`, `typescript` `^5.6.3`, `@types/react` `^18.3.12`, `@types/react-dom` `^18.3.1` | |
| Styling (dev) | `tailwindcss` `^3.4.14`, `postcss` `^8.4.47`, `autoprefixer` `^10.4.20`, `@tailwindcss/typography` `^0.5.15` | |
| Unit/component tests (dev) | `vitest` `^2.1.4`, `jsdom` `^25.0.1`, `@testing-library/react` `^16.0.1`, `@testing-library/dom` `^10.4.0`, `@testing-library/jest-dom` `^6.6.2`, `@testing-library/user-event` `^14.5.2` | |

Browser-level verification uses Playwright from the shared Python `.venv` (ADR-0005,
ADR-0020), not an npm package.

### Scripts (`frontend/package.json`)

```json
{"dev": "vite", "build": "tsc -b && vite build", "preview": "vite preview",
 "test": "vitest run", "typecheck": "tsc -b --noEmit"}
```

### Config files (owned by T-011 only)

`package.json`, `package-lock.json`, `vite.config.ts` (React plugin; dev proxy `/api` ->
`http://127.0.0.1:8000`; vitest `environment: "jsdom"`, `setupFiles: ["src/test/setup.ts"]`,
`include: ["src/**/*.test.{ts,tsx}"]`), `tsconfig.json` / `tsconfig.app.json` /
`tsconfig.node.json` (`strict: true`, path alias `@/` -> `src/`), `tailwind.config.ts`
(`darkMode: "class"`, colors bound to CSS variables, typography plugin), `postcss.config.js`,
`index.html`, `src/test/setup.ts`.

Tailwind v3 (config-file based) rather than v4 because its config is a stable,
widely-documented contract for the token mapping in ADR-0019.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Radix primitives + our own Tailwind components (chosen) | Accessible behaviour (focus, keyboard, ARIA) for free; full visual control | We style every component ourselves (that is the design-system ticket) |
| B. A full component kit (MUI, Chakra) | Fast | Fights Tailwind tokens; heavy; generic look |
| C. Headless UI | Small | Fewer primitives (no toast, select is limited) |
| Charts: Recharts (chosen) vs. Chart.js vs. visx | React-native API, SVG (crisp, themeable via CSS vars) | Bundle size moderate |
| Tests: Vitest + Testing Library (chosen) vs. Jest | Shares Vite config; fast | — |

## Consequences

- Wave-4 tickets may not add packages; a missing primitive is a `BLOCKED` report.
- `npm ci` (run by `scripts/verify.sh`) needs network access on the build machine.
