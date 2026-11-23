# Product decisions

The product owner's decisions, and the defaults the Supervisor chose while waiting for one.
Each entry records the date, the question, the answer and what changed, with links.
Open questions also appear in [tickets/plan.json](../tickets/plan.json) (`open_questions`).

## Confirmed by the product owner

| Date | Question | Answer | What changed |
|---|---|---|---|
| 2026-11-23 | Should the backend be FastAPI? | Yes: FastAPI, as in the product brief. | [ADR-0007](adr/0007-stack-and-module-layout.md), now [ADR-0024](adr/0024-stack-and-module-layout-v2.md). The database part changed later the same day (see the PostgreSQL row). |
| 2026-11-23 | Q-001: Who needs to approve each founder's 83(b) form? | **Only that founder** (each founder approves just their own 83(b)). | Confirms the default; no change. [ADR-0014](adr/0014-founding-documents-and-signoff-state-machine.md); [T-004](../tickets/T-004-signoff-state-machine.md), [T-006](../tickets/T-006-law-agent-and-document-drafting.md), [T-015](../tickets/T-015-legal-service-cap-table-documents-signoff.md). |
| 2026-11-23 | Q-002: Which hosting service publishes the website? | **Netlify.** | Confirms the default; no change. [ADR-0011](adr/0011-external-service-ports-rdap-and-hosting.md); [T-008](../tickets/T-008-website-agent-renderer-and-netlify.md), [T-016](../tickets/T-016-api-core-composition-and-demo-seed.md). |
| 2026-11-23 | Q-003: Can a document be edited after everyone approved it? | **Yes, everyone re-approves** (the edit creates a new version and cancels the other approvals). | Confirms the default. With electronic signatures the editor now signs the new version in the same step ([ADR-0031](adr/0031-electronic-signatures-and-signed-pdfs.md)); [T-004](../tickets/T-004-signoff-state-machine.md), [T-020](../tickets/T-020-legal-signoff-and-audit-screens.md). |
| 2026-11-23 | Q-004: When does founder vesting start? | **On the incorporation date.** | Confirms the default; no change. [ADR-0013](adr/0013-case-validation-cap-table-and-vesting-rules.md); [T-003](../tickets/T-003-cap-table-vesting-and-exports.md), [T-021](../tickets/T-021-cap-table-screen.md). |
| 2026-11-23 | Q-005: Which website pages are used when the founder doesn't say? | **Home, About, Services, Contact.** | Confirms the default; no change. [ADR-0008](adr/0008-shared-domain-contracts.md), [ADR-0015](adr/0015-website-generation-qa-and-deploy-loop.md); [T-008](../tickets/T-008-website-agent-renderer-and-netlify.md), [T-009](../tickets/T-009-qa-agent-site-checks.md). |
| 2026-11-23 | Which AI backends, and where may each run? | One setting, `LLM_PROVIDER`: `fake` (tests, reliable demo), `claude_code` (the owner's own machine through the Claude Code CLI and the owner's login, never for serving others; warns at start, refuses in production), `anthropic` (production, API key, default model `claude-opus-5-5`, cheaper model per agent configurable), `deepseek`, `groq`. | New [ADR-0021](adr/0021-settings-environments-and-production-guards.md) and [ADR-0022](adr/0022-llm-providers-fake-claude-code-anthropic-deepseek-groq.md) (supersede the provider part of ADR-0010); new tickets [T-024](../tickets/T-024-llm-provider-claude-code-cli.md) and [T-025](../tickets/T-025-llm-providers-anthropic-and-openai-compatible.md). |
| 2026-11-23 | Reliability | Every AI and outside call has a timeout and retries on temporary errors; long work runs as tracked background jobs; no raw error reaches a founder. | New [ADR-0023](adr/0023-reliability-timeouts-retries-and-failure-states.md), [ADR-0028](adr/0028-background-jobs-queue-worker-and-scheduler.md); [T-030](../tickets/T-030-background-jobs-runner-worker-and-scheduler.md); criteria added to T-007, T-008, T-013, T-022. |
| 2026-11-23 | Demo video | A first-class feature: one command records the real app at 1920x1080 with captions, every agent showing tangible output; `reliable` (offline, identical every run) and `live` modes; WebM + MP4, screenshots and artifacts per run; the reliable demo is a gated recorded run that must pass three times in a row; last integration wave. | New [ADR-0037](adr/0037-demo-video-scripted-recording-reliable-and-live-modes.md); [T-046](../tickets/T-046-demo-video-reliable-and-live.md) (wave 6). |
| 2026-11-23 | A complete, sellable product, not a demo | Accounts and co-founder invites; authorization on every endpoint; electronic signatures with signed PDFs; Stripe plans and billing (test mode by default); transactional email with 83(b) reminders; PostgreSQL with versioned migrations, Docker and CI; security hardening; landing, pricing, Terms and Privacy pages; data export and deletion; admin area; brand-level polish. The founder switcher is demo-mode only. | New ADRs [0024](adr/0024-stack-and-module-layout-v2.md)–[0036](adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md) supersede ADR-0007, 0012, 0017, 0018, 0019, 0020 and parts of 0008, 0010, 0014. Wave 0 now carries every cross-cutting contract; the backlog grew from 23 to 46 tickets in 7 waves ([BACKLOG](../tickets/BACKLOG.md)). |
| 2026-11-23 | Database | PostgreSQL in production, SQLite for development and tests, with versioned migrations. | [ADR-0027](adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md) supersedes ADR-0012; [T-001](../tickets/T-001-foundation-skeleton-contracts-and-fakes.md), [T-005](../tickets/T-005-persistence-sqlite-repository.md), [T-034](../tickets/T-034-docker-compose-ci-and-operations-guide.md). |

## Defaults waiting for confirmation (open questions)

Each default is already in the plan. If the owner picks another option, the Supervisor
updates the data or writes a superseding ADR and updates the tickets listed.

| Id | Question | Default applied | Where it lives |
|---|---|---|---|
| Q-006 | How should founders pay, and how much? | **Free plan + "Launch" at $39 per month or $390 per year.** Free: one company, chat with every agent, name checks, cap table, website preview, checklist, 83(b) reminders, 300 AI messages a month. Launch adds documents, e-signatures, signed PDF/Word downloads, website publishing, 5 companies, 5,000 AI messages a month. | [ADR-0030](adr/0030-plans-billing-stripe-and-entitlements.md) (`PLANS`); [T-001](../tickets/T-001-foundation-skeleton-contracts-and-fakes.md), [T-029](../tickets/T-029-billing-plans-stripe-checkout-portal-and-webhooks.md), [T-043](../tickets/T-043-marketing-pricing-and-legal-pages.md) |
| Q-007 | What is the product called? | **Charterly** (one setting, `BRAND_NAME`; we check the domain and trademark before launch). | [ADR-0035](adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md); [T-001](../tickets/T-001-foundation-skeleton-contracts-and-fakes.md), [T-011](../tickets/T-011-frontend-design-system-and-app-shell.md) |
| Q-008 | When a founder deletes their account, what happens to a company they share with co-founders? | **The company stays with the co-founders**; the signed documents keep the departed founder's typed signature as the legal record; solo companies are deleted. | [ADR-0034](adr/0034-deployment-operations-privacy-and-admin.md); [T-037](../tickets/T-037-privacy-data-export-and-account-deletion.md), [T-044](../tickets/T-044-settings-team-billing-and-privacy-screens.md) |

## Smaller product choices the Supervisor made (tell us if you disagree)

These follow the brief closely, so they are not open questions, but founders will notice them:

- **Several companies per account**, limited by plan (Free 1, Launch 5) ([ADR-0030](adr/0030-plans-billing-stripe-and-entitlements.md)).
- **A company's plan is its creator's plan**, so an invited co-founder can sign and publish within that company without paying ([ADR-0030](adr/0030-plans-billing-stripe-and-entitlements.md)).
- **You must confirm your email before you can sign** a document; everything else works before confirmation ([ADR-0026](adr/0026-accounts-sessions-request-context-and-authorization.md)).
- **Your typed signature must match your name as written in the documents** ([ADR-0031](adr/0031-electronic-signatures-and-signed-pdfs.md)).
- **83(b) reminders are free on every plan**, because missing that deadline is costly ([ADR-0029](adr/0029-transactional-email-notifications-and-83b-reminders.md)).
- **Tax IDs and card numbers typed into the chat are removed** before anything is stored or sent to the AI, with a short explanation ([ADR-0033](adr/0033-security-hardening.md)).
- **Admins see account metadata only**, never chat, documents or websites ([ADR-0034](adr/0034-deployment-operations-privacy-and-admin.md)).
- **Terms, Privacy and Disclaimer pages ship as clearly marked drafts** with placeholders for your legal company name, contact email and governing-law state; have a lawyer review them before launch ([T-043](../tickets/T-043-marketing-pricing-and-legal-pages.md)).
- Kept from the first plan: equity up to two decimals; the 83(b) deadline is 30 calendar days (warning under 8 days); founders confirm a summary before documents are drafted; five name ideas per request checked on .com/.co/.io, with "couldn't check" never shown as available; chat replies arrive whole with a typing indicator.
- **No longer true:** "no real sign-in or e-signature" from the first plan. Real accounts and electronic signatures are now part of v1; "act as founder" exists only in demo mode.
