# ADR-0005: Frontend verification and browser-recorded runs

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Harness operator, product owner |
| **Tickets** | — |
| **Scope** | `scripts/verify.sh`, `frontend/package.json` conventions, `evidence/` for UI tickets, `requirements.txt` |

## Context

The product owner requires a good-looking frontend, so the UI is a React + TypeScript +
Vite + Tailwind app (product brief), not Streamlit. ADR-0003's gate only knew about
`pytest` and a Python feature run. A UI can build and pass unit tests and still look
broken, so "the feature works" has to be shown in a real browser.

## Decision

This ADR extends ADR-0003 (it does not replace it):

1. **Frontend lives in `frontend/`** with `package.json` and a committed
   `package-lock.json`. Its scripts must include `build` (type-check + production build)
   and `test` (unit/component tests that exit when done, e.g. `vitest run`).
2. **`scripts/verify.sh` runs the frontend checks** whenever `frontend/package.json`
   exists: install (`npm ci`, re-run when the lockfile is newer than `node_modules`),
   `npm run build`, `npm test`. A failure fails the gate, like a failing `pytest`.
3. **npm dependencies are an architecture decision.** The set of allowed npm packages
   is fixed by the Supervisor in an ADR. One ticket per wave owns `frontend/package.json`
   and the frontend config files; other UI tickets in that wave may not add packages
   (they report `BLOCKED` if they need one).
4. **UI tickets record in a browser.** Their `evidence/T-NNN/feature_run.py` uses
   Playwright (in the shared `.venv`, Chromium installed) to start the backend with
   fakes and the built frontend, drive the user flow the ticket delivers, assert on
   what is visible, and save screenshots to `evidence/T-NNN/` at desktop (1280px) and
   phone (390px) widths in light and dark mode. The Reviewer looks at the screenshots
   as part of the review, judging them against the design quality bar in the brief.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Build + unit tests + Playwright screenshots in the recorded run (chosen) | Proves it renders and works; reviewers see the real UI; evidence lives in git | Screenshots add binary files to the repo (small PNGs) |
| B. Build + unit tests only | Fast | "Looks good" is never checked |
| C. Full visual-regression service | Pixel-diff history | Extra service and baseline churn; overkill for now |

## Consequences

- Every merged UI change has screenshots a person can look at without running anything.
- Gate runs take longer when the frontend is involved (install + build).
- The Supervisor must name the npm package set up front, like `requirements.txt` for Python.
