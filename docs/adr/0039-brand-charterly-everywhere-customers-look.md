# ADR-0039: Brand: "Charterly" everywhere customers look

| | |
|---|---|
| **Status** | Superseded by [ADR-0041](0041-brand-keelstart-everywhere-customers-look.md) |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor, product owner (Q-007: Charterly) |
| **Tickets** | T-001 (constant, setting, greeting), T-011 (brand kit, titles), T-043 (landing, pricing, legal pages), T-028 (emails), T-031 (PDF and Word), T-015 (passes the brand), T-037 (export file name), T-046 (demo video), T-012 (Manager copy) |
| **Scope** | `domain/constants.py` `BRAND_NAME`, `Settings.brand_name`, `frontend/src/brand/`, email rendering, PDF/DOCX rendering, export and demo output |

## Context

ADR-0035 used "Charterly" as a working name pending Q-007. The product owner chose
**Charterly** and asked that it be the product name everywhere (brand, landing page,
emails, PDFs) while staying one setting. This ADR **supersedes the "Brand" section of
ADR-0035** (routes, layouts and feature boundaries there are unchanged) and adds brand
placement to the email (ADR-0029) and PDF / Word (ADR-0031) outputs.

## Decision

- **One source.** `BRAND_NAME = "Charterly"` in `domain/constants.py` is the default of
  `Settings.brand_name` (env `BRAND_NAME`). Backend code reads `settings.brand_name`;
  the frontend reads `PublicConfig.brand_name` with the compiled fallback "Charterly" in
  `src/brand/brand.ts`. No other source file hard-codes the name: a T-001 test finds the
  literal in `launch_agents/` only in `domain/constants.py`, and a T-011 test finds it in
  `frontend/src/` only inside `src/brand/` (test files excepted). Copy such as "Signed
  with Charterly" is built from the setting, never typed out.
- **Brand kit** (`src/brand/`, T-011): word mark "Charterly" with the folded-document
  check mark in deep indigo, favicon set, Open Graph image (word mark + tagline),
  tagline **"Launch your company with a team of AI agents"**, disclaimer line "Not legal
  advice. Charterly is not a law firm."
- **Web:** every page title is `{Page} · Charterly` (landing: `Charterly · Launch your
  company with a team of AI agents`); header and footer show the word mark; the footer
  says "© {year} [COMPANY LEGAL NAME]. Charterly is a product of [COMPANY LEGAL NAME]."
  until the owner fills the placeholder (T-043 constant).
- **Emails:** subject prefix `Charterly: `; the HTML header shows the word mark as text
  (no remote images); the footer names Charterly; when `EMAIL_FROM` has no display name
  the sender is shown as `Charterly <address>`.
- **Signed PDF:** document metadata title = document title, author = company name,
  creator and producer = "Charterly"; the certificate of completion is titled
  "Certificate of completion - Charterly e-signature record"; the page footer keeps the
  ADR-0031 line and appends "Signed with Charterly". **Word copy:** core properties
  creator "Charterly"; first page note "Editable copy from Charterly - not the signed
  record". The documents themselves never name Charterly as a party.
  `render_signed_pdf` and `render_docx` gain a keyword `brand_name: str = BRAND_NAME`.
- **Other outputs:** data export file `charterly-export-{date}.zip` (slug of the brand);
  the Manager greets as "the Manager at Charterly"; the demo video's opening title card
  and end card show the word mark.
- **Stays internal:** the Python package `launch_agents`, the `LAUNCH_*` environment
  variables, cookie names (`la_session`, `la_csrf`) and storage keys. Customers never
  see them, and renaming them would only churn every ticket.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Brand as one setting used by every customer-facing output (chosen) | Owner's choice; rename stays one value | Tests must guard against hard-coded names |
| B. Hard-code "Charterly" | Slightly simpler | A later rename touches every ticket |
| C. Also rename the internal package and env prefix | Consistent internals | Large churn for nothing a customer sees |

## Consequences

- Before launch the owner checks the domain and trademark for "Charterly" and fills
  `[COMPANY LEGAL NAME]` on the legal pages and footer.
- Renaming later = `BRAND_NAME` plus the compiled fallback and the logo artwork.
