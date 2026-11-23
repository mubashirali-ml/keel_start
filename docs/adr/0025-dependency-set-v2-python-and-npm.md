# ADR-0025: Dependency set v2 (Python and npm)

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor (the operator installs them; `requirements.txt` is harness-owned) |
| **Tickets** | T-001 and every ticket that imports a new package; T-011 (npm) |
| **Scope** | `requirements.txt` (operator), `frontend/package.json` (T-011) |

## Context

ADR-0002 makes a new dependency a Supervisor decision recorded in an ADR, and
`requirements.txt` is owned by the harness operator, not by any ticket. ADR-0018 fixed
the npm set for the first plan. The sellable product needs migrations, a Postgres
driver, password hashing, payments, PDF/DOCX output and email validation, and the
frontend needs form handling and a few more primitives. This ADR **supersedes ADR-0018**
(its package table; its scripts and config-file rules are restated here unchanged).

## Decision

### Python: already approved (in `requirements.txt` today)

fastapi, uvicorn[standard], httpx, pydantic, sqlalchemy, python-dotenv, langgraph,
langgraph-checkpoint-sqlite, langchain-openai, langchain-core, requests, openpyxl,
pytest, playwright, **anthropic** (ADR-0022), **imageio-ffmpeg** (ADR-0037).

### Python: new packages the operator must add before delivery

| Package (pip spec) | Why | Used by |
|---|---|---|
| `alembic>=1.13` | versioned database migrations (ADR-0027) | T-001, T-005, T-034 |
| `psycopg[binary]>=3.2` | PostgreSQL driver (`postgresql+psycopg://`) | T-005, T-034 |
| `argon2-cffi>=23.1` | argon2id password hashing (ADR-0026) | T-026 |
| `stripe>=11.0` | Stripe Checkout, customer portal, webhooks (ADR-0030) | T-029 |
| `reportlab>=4.2` | signed PDF with signature page (ADR-0031) | T-031 |
| `python-docx>=1.1` | editable Word copy of each document (placeholders filled offline) | T-031 |
| `email-validator>=2.2` | email address validation (pydantic `EmailStr`) | T-001, T-026, T-027 |

Deliberately **not** added (standard library or our own small code instead): Celery /
Redis / RQ (jobs, ADR-0028), slowapi (rate limits, ADR-0033), itsdangerous (tokens are
random + hashed), Jinja2 (email templates use `string.Template` + `html.escape`),
tenacity (ADR-0023), sentry-sdk (pluggable hook, ADR-0034), PyYAML (no YAML parsing at runtime).

Until the operator installs them, `tests/conftest.py` (T-001) marks tests that import a
missing package as skipped with a clear reason, so wave 0 can merge. A wave-1 ticket
whose package is still missing from the shared `.venv` reports `BLOCKED` instead of
working around it; skipped tests never count as passing acceptance criteria.

### npm (T-011 is the only owner of `frontend/package.json`; versions are minimum lines, the lockfile pins)

Everything in ADR-0018 stays: react, react-dom `^18.3.1`; react-router-dom `^6.28.0`;
@tanstack/react-query `^5.59.0`; @radix-ui dialog `^1.1.2`, tabs `^1.1.1`,
dropdown-menu `^2.1.2`, select `^2.1.2`, tooltip `^1.1.3`, toast `^1.2.2`, checkbox
`^1.1.2`, progress `^1.1.0`, avatar `^1.1.1`, scroll-area `^1.2.0`, slot `^1.1.0`;
lucide-react `^0.454.0`; recharts `^2.13.0`; react-markdown `^9.0.1`; clsx `^2.1.1`,
tailwind-merge `^2.5.4`, class-variance-authority `^0.7.0`;
@fontsource-variable/inter `^5.1.0`; dev: vite `^5.4.10`, @vitejs/plugin-react `^4.3.3`,
typescript `^5.6.3`, @types/react `^18.3.12`, @types/react-dom `^18.3.1`, tailwindcss
`^3.4.14`, postcss `^8.4.47`, autoprefixer `^10.4.20`, @tailwindcss/typography `^0.5.15`,
vitest `^2.1.4`, jsdom `^25.0.1`, @testing-library/react `^16.0.1`,
@testing-library/dom `^10.4.0`, @testing-library/jest-dom `^6.6.2`,
@testing-library/user-event `^14.5.2`.

Added:

| Package | Version | Why |
|---|---|---|
| `react-hook-form` | `^7.53.0` | sign-up, login, settings, e-signature forms |
| `zod` | `^3.23.8` | client-side form schemas mirroring the API limits |
| `@hookform/resolvers` | `^3.9.0` | zod resolver for react-hook-form |
| `@radix-ui/react-label` | `^2.1.0` | accessible form labels |
| `@radix-ui/react-switch` | `^1.1.1` | settings toggles |
| `@radix-ui/react-radio-group` | `^1.2.1` | monthly / yearly plan choice |
| `@radix-ui/react-popover` | `^1.1.2` | account menu, help popovers |

No Stripe npm package: Checkout and the portal are full-page redirects. Scripts and
config files are as in ADR-0018 (`dev`, `build` = `tsc -b && vite build`, `preview`,
`test` = `vitest run`, `typecheck`; Vite proxy `/api`; Tailwind v3 config).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Small set of mature, single-purpose packages (chosen) | Each solves one hard problem (crypto, payments, PDF, migrations) | Seven new Python packages to install |
| B. Hand-roll password hashing / PDF | No installs | Security and quality risk; reviewers would reject it |
| C. Full frameworks (Celery, Django) | Batteries included | Heavy; replaces decisions already made |

## Consequences

- The operator installs the seven Python packages once; the owner brief lists them.
- Wave-4 UI tickets may not add npm packages; a missing one is a `BLOCKED` report.
