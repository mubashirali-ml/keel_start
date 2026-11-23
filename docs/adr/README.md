# Architecture Decision Records

Why ADRs and how we use them: [ADR-0001](0001-record-architecture-decisions.md).
New ADR: copy [0000-template.md](0000-template.md) to the next free number.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-multi-agent-delivery-process.md) | Multi-agent delivery process (Supervisor, Builders, Reviewer) | Accepted |
| [0003](0003-merge-gate-tests-and-recorded-run.md) | Merge gate: tests plus a recorded feature run | Accepted |
| [0004](0004-supervisor-modes-human-and-auto.md) | Supervisor modes: human-in-the-loop and autonomous | Accepted |
| [0005](0005-frontend-verification-and-browser-recordings.md) | Frontend verification and browser-recorded runs | Accepted |
| [0006](0006-product-owner-supervisor-interaction.md) | Product owner ↔ Supervisor interaction | Accepted |
| [0007](0007-stack-and-module-layout.md) | Stack and module layout (FastAPI + SQLite backend) | Superseded by [0024](0024-stack-and-module-layout-v2.md) |
| [0008](0008-shared-domain-contracts.md) | Shared domain contracts (types, constants, helpers, errors, views) | Accepted (partly superseded by 0026, 0027) |
| [0009](0009-agent-message-and-handoff-protocol.md) | Agent message and handoff protocol | Accepted |
| [0010](0010-llm-provider-abstraction-and-fake.md) | LLM provider abstraction and deterministic fake | Partly superseded by 0021, 0022 |
| [0011](0011-external-service-ports-rdap-and-hosting.md) | External service ports: RDAP domain checks and Netlify hosting | Accepted |
| [0012](0012-persistence-and-data-model.md) | Persistence and data model (SQLite via SQLAlchemy) | Superseded by [0027](0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md) |
| [0013](0013-case-validation-cap-table-and-vesting-rules.md) | Deterministic rules: case validation, cap table and vesting | Accepted |
| [0014](0014-founding-documents-and-signoff-state-machine.md) | Founding documents and the multi-party sign-off state machine | Partly superseded by 0031 |
| [0015](0015-website-generation-qa-and-deploy-loop.md) | Website generation, QA checks and the fix-and-deploy loop | Accepted |
| [0016](0016-registration-guide-data-and-checklist.md) | Registration guide data and checklist | Accepted |
| [0017](0017-services-and-http-api-surface.md) | Application services and the HTTP API surface | Superseded by [0032](0032-services-and-http-api-v2.md) |
| [0018](0018-frontend-stack-and-npm-package-set.md) | Frontend stack and the approved npm package set | Superseded by [0025](0025-dependency-set-v2-python-and-npm.md) |
| [0019](0019-frontend-design-system-and-app-layout.md) | Frontend design system, app layout and feature boundaries | Superseded by [0035](0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md) |
| [0020](0020-ui-recorded-runs-and-demo-seeding.md) | UI recorded runs: app launch with fakes, screenshot matrix and demo seeding | Superseded by [0036](0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md) |
| [0021](0021-settings-environments-and-production-guards.md) | Settings, environments (APP_ENV) and production guards | Accepted |
| [0022](0022-llm-providers-fake-claude-code-anthropic-deepseek-groq.md) | LLM providers: fake, claude_code, anthropic, deepseek, groq | Accepted |
| [0023](0023-reliability-timeouts-retries-and-failure-states.md) | Reliability: timeouts, retries and failure states | Accepted |
| [0024](0024-stack-and-module-layout-v2.md) | Stack and module layout v2 (sellable product) | Accepted |
| [0025](0025-dependency-set-v2-python-and-npm.md) | Dependency set v2 (Python and npm) | Accepted |
| [0026](0026-accounts-sessions-request-context-and-authorization.md) | Accounts, sessions, the request context and authorization | Accepted |
| [0027](0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md) | Persistence v2: PostgreSQL and SQLite, Alembic migrations, data model | Accepted |
| [0028](0028-background-jobs-queue-worker-and-scheduler.md) | Background jobs: queue, worker and scheduler | Accepted |
| [0029](0029-transactional-email-notifications-and-83b-reminders.md) | Transactional email, notifications and 83(b) reminders | Accepted |
| [0030](0030-plans-billing-stripe-and-entitlements.md) | Plans, billing with Stripe, and entitlements | Accepted |
| [0031](0031-electronic-signatures-and-signed-pdfs.md) | Electronic signatures and signed PDF / Word downloads | Accepted |
| [0032](0032-services-and-http-api-v2.md) | Application services and the HTTP API v2 (authenticated) | Accepted |
| [0033](0033-security-hardening.md) | Security hardening | Accepted |
| [0034](0034-deployment-operations-privacy-and-admin.md) | Deployment, operations, privacy controls and the admin area | Accepted |
| [0035](0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md) | Frontend v2: brand, routes, layouts and feature boundaries | Accepted |
| [0036](0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md) | UI recorded runs with accounts, demo mode and demo seeding v2 | Accepted |
| [0037](0037-demo-video-scripted-recording-reliable-and-live-modes.md) | Demo video: scripted browser recording in reliable and live modes | Accepted |
