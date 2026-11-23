# ADR-0041: Brand: "Keelstart" everywhere customers look

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor, product owner (rename from Charterly; tagline: open question Q-010) |
| **Tickets** | T-047 (constant, `.env.example`, foundation tests), T-011 (brand kit, logo, titles), T-043 (landing, pricing, legal pages), T-028 (emails), T-031 (PDF and Word), T-015 (passes the brand), T-016 (`/api/config` default), T-037 (export file name), T-046 (demo video), T-023 (journey checks) |
| **Scope** | `domain/constants.py` `BRAND_NAME`, `Settings.brand_name`, `frontend/src/brand/`, email rendering, PDF/DOCX rendering, export and demo output |

## Context

ADR-0039 made **Charterly** the product name everywhere customers look, as one setting.
The product owner has since renamed the product **Keelstart**: charterly.com is taken and
keelstart.com is free. "Laying the keel" is the first step of building a ship, the
backbone everything else rests on, which is what the product does for a new company.
The owner suggested a simple sailboat / keel logo mark and asked that the name stay a
single setting.

T-001 has already merged with `BRAND_NAME = "Charterly"` in `domain/constants.py`, the
same value in `.env.example`, and foundation tests that spell it out. Those files have no
owner any more, so a small follow-up ticket (T-047) changes them.

This ADR **supersedes ADR-0039** in full. Everything in ADR-0039 carries over with the
name changed, plus the new logo; ADR-0035's brand section stays superseded.

## Decision

- **One source.** `BRAND_NAME = "Keelstart"` in `domain/constants.py` is the default of
  `Settings.brand_name` (env `BRAND_NAME`). Backend code reads `settings.brand_name`;
  the frontend reads `PublicConfig.brand_name` with the compiled fallback "Keelstart" in
  `src/brand/brand.ts`. No other source file hard-codes the name: the T-001 foundation
  test (updated by T-047) finds the literal in `launch_agents/` only in
  `domain/constants.py`, and a T-011 test finds it in `frontend/src/` only inside
  `src/brand/` (test files excepted). Copy such as "Signed with Keelstart" is built from
  the setting, never typed out. The old name "Charterly" appears in no source file.
- **Tests never depend on the default's spelling** outside the two guard tests and the
  T-047 constant test: they compare against `BRAND_NAME` / `settings.brand_name`, or pass
  `brand_name=` explicitly. This lets wave-1 tickets merge before or after T-047.
- **Logo mark** (`src/brand/`, T-011): a simple sailboat seen side-on, as one inline SVG
  in `primary`: a triangular sail above a shallow hull, with a short keel fin under the
  hull's centre. Flat shapes, no gradients, legible at 16 px (favicon) and in one colour
  (`currentColor` variant for dark backgrounds and emails). The word mark "Keelstart"
  sits to its right in the heading font. The mark replaces ADR-0039's folded document.
- **Colour:** primary is a deep navy blue (a bluer take on the planned deep indigo, still
  AA on every surface in light and dark per the T-011 contrast test); agent accents are
  unchanged (ADR-0019).
- **Tagline** **"Launch your company with a team of AI agents"** (default pending
  Q-010; it is one constant in `src/brand/`). **Disclaimer line:** "Not legal advice.
  Keelstart is not a law firm." The Open Graph image shows the mark, word mark and tagline.
- **Web:** every page title is `{Page} · Keelstart` (landing: `Keelstart · Launch your
  company with a team of AI agents`); header and footer show the logo; the footer says
  "© {year} [COMPANY LEGAL NAME]. Keelstart is a product of [COMPANY LEGAL NAME]." until
  the owner fills the placeholder (T-043 constant).
- **Emails:** subject prefix `Keelstart: `; the HTML header shows the word mark as text
  (no remote images); the footer names Keelstart; when `EMAIL_FROM` has no display name
  the sender is shown as `Keelstart <address>`.
- **Signed PDF:** document metadata title = document title, author = company name,
  creator and producer = "Keelstart"; the certificate of completion is titled
  "Certificate of completion - Keelstart e-signature record"; the page footer keeps the
  ADR-0031 line and appends "Signed with Keelstart". **Word copy:** core properties
  creator "Keelstart"; first page note "Editable copy from Keelstart - not the signed
  record". The documents themselves never name Keelstart as a party.
  `render_signed_pdf` and `render_docx` keep the keyword `brand_name: str = BRAND_NAME`
  (the signature is unchanged; only the default value moves).
- **Other outputs:** data export file `keelstart-export-{date}.zip` (slug of the brand);
  the Manager greets as "the Manager at Keelstart"; the demo video's opening title card
  and end card show the logo, word mark and tagline.
- **Stays internal:** the Python package `launch_agents`, the `LAUNCH_*` environment
  variables, cookie names (`la_session`, `la_csrf`) and storage keys. Customers never
  see them.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Change the one setting and its default, plus the logo (chosen) | Owner's choice; the ADR-0039 design makes it one value plus artwork | A small follow-up ticket for the already-merged foundation files |
| B. Keep "Charterly" in code and set `BRAND_NAME=Keelstart` only in deployment | No code change | Tests, fakes, recorded runs and the demo video would still say Charterly |
| C. Also rename the internal package and env prefix | Consistent internals | Large churn for nothing a customer sees |

## Consequences

- T-047 (wave 1) changes the constant, `.env.example` and the foundation tests; nothing
  else in merged code names the brand (the greeting already reads `BRAND_NAME`).
- Before launch the owner registers keelstart.com, runs a trademark check for
  "Keelstart", and fills `[COMPANY LEGAL NAME]` on the legal pages and footer.
- Renaming again = `BRAND_NAME`, the compiled fallback and the logo artwork.
