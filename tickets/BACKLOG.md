# Backlog

Plan for building [the product brief](../docs/product-brief.md). Architecture decisions: [docs/adr/](../docs/adr/README.md).
Machine-readable twin: [plan.json](plan.json). Product decisions log: [product-decisions.md](../docs/product-decisions.md).

Tickets in the same wave own disjoint paths and run in parallel; each depends only on earlier waves.
47 tickets in 7 waves.

**Delivery status (2026-11-23).** T-001 is `merged` (operator ran the merge gate: all checks passed,
590 tests, merge commit `7ad2082`). From now on the gate runs in the operator's session and approved
tickets come back as `approved` for the operator to merge
([ADR-0040](../docs/adr/0040-merge-gate-runs-in-the-operators-session.md)). **Next wave: 1** (21 tickets,
including the new T-047 for the Keelstart rename and support wording).

## Wave 0

Groundwork: the shared vocabulary of the product, the contracts for accounts, billing, email and background jobs, the database layout, and stand-ins for the AI and every outside service, so twenty-one pieces can be built at the same time next. Nothing to look at yet.

| Ticket | Title | Depends on | Owns | Status |
|---|---|---|---|---|
| [T-001](T-001-foundation-skeleton-contracts-and-fakes.md) | Foundation: package skeleton, shared and cross-cutting contracts, schema, fakes and typed stubs | — | `launch_agents/`<br>`migrations/`<br>`alembic.ini`<br>`tests/conftest.py`<br>`tests/test_foundation.py`<br>`pytest.ini`<br>`.env.example`<br>`evidence/T-001/`<br>`prs/T-001.md` | merged |

## Wave 1

Twenty-one pieces built side by side: the automatic rules (equity, vesting, 83(b), cap table, approvals), saving to SQLite and PostgreSQL, the five specialist agents, the AI connections (your own Claude Code login on your machine, the Anthropic API for production), accounts and co-founder invites, email, Stripe billing for the Free, Launch and Team plans, background jobs, signed PDFs, security and logging, the app's look and feel, and the switch of the built-in name to Keelstart. You can open the design gallery and see the Keelstart brand and logo in light and dark mode.

| Ticket | Title | Depends on | Owns | Status |
|---|---|---|---|---|
| [T-002](T-002-case-validation-rules.md) | Case validation rules (equity, vesting, 83(b), missing facts) | T-001 | `launch_agents/rules/validation.py`<br>`tests/test_validation.py`<br>`evidence/T-002/`<br>`prs/T-002.md` | todo |
| [T-003](T-003-cap-table-vesting-and-exports.md) | Cap Table Builder: share allocation, vesting schedule, CSV and Excel export | T-001 | `launch_agents/rules/cap_table.py`<br>`launch_agents/rules/exports.py`<br>`tests/test_cap_table.py`<br>`tests/test_cap_table_exports.py`<br>`evidence/T-003/`<br>`prs/T-003.md` | todo |
| [T-004](T-004-signoff-state-machine.md) | Multi-party sign-off state machine with e-signature evidence and audit entries | T-001 | `launch_agents/signoff/`<br>`tests/test_signoff.py`<br>`evidence/T-004/`<br>`prs/T-004.md` | todo |
| [T-005](T-005-persistence-sqlite-repository.md) | Persistence: engine for SQLite and PostgreSQL, migrations, and the case Repository | T-001 | `launch_agents/persistence/engine.py`<br>`launch_agents/persistence/repository.py`<br>`tests/test_persistence.py`<br>`tests/test_migrations.py`<br>`evidence/T-005/`<br>`prs/T-005.md` | todo |
| [T-006](T-006-law-agent-and-document-drafting.md) | Law Agent: legal Q&A, issue spotting and founding-document drafting | T-001 | `launch_agents/agents/law/`<br>`tests/test_law_agent.py`<br>`tests/test_law_documents.py`<br>`evidence/T-006/`<br>`prs/T-006.md` | todo |
| [T-007](T-007-name-agent-and-rdap-checks.md) | Name Agent with live RDAP domain checks | T-001 | `launch_agents/agents/name/`<br>`launch_agents/adapters/rdap.py`<br>`tests/test_name_agent.py`<br>`tests/test_rdap.py`<br>`evidence/T-007/`<br>`prs/T-007.md` | todo |
| [T-008](T-008-website-agent-renderer-and-netlify.md) | Website Agent: site content, static renderer and Netlify deploy adapter | T-001 | `launch_agents/agents/website/`<br>`launch_agents/adapters/netlify.py`<br>`tests/test_website_agent.py`<br>`tests/test_site_renderer.py`<br>`tests/test_netlify.py`<br>`evidence/T-008/`<br>`prs/T-008.md` | todo |
| [T-009](T-009-qa-agent-site-checks.md) | QA Agent: requirement and quality checks for generated websites | T-001 | `launch_agents/agents/qa/`<br>`tests/test_qa_agent.py`<br>`evidence/T-009/`<br>`prs/T-009.md` | todo |
| [T-010](T-010-registration-guide-agent.md) | Registration Guide Agent with curated Delaware and Wyoming data | T-001 | `launch_agents/agents/guide/`<br>`tests/test_guide_agent.py`<br>`evidence/T-010/`<br>`prs/T-010.md` | todo |
| [T-011](T-011-frontend-design-system-and-app-shell.md) | Frontend foundation: brand, design system, themes, app shell and layouts, typed API client with auth, UI-run helper | T-001 | `frontend/`<br>`launch_agents/devtools/`<br>`tests/test_devtools.py`<br>`evidence/T-011/`<br>`prs/T-011.md` | todo |
| [T-024](T-024-llm-provider-claude-code-cli.md) | LLM provider `claude_code`: the Claude Code CLI in print mode for local development and live demos | T-001 | `launch_agents/llm/claude_code.py`<br>`tests/test_llm_claude_code.py`<br>`evidence/T-024/`<br>`prs/T-024.md` | todo |
| [T-025](T-025-llm-providers-anthropic-and-openai-compatible.md) | LLM providers for production: `anthropic` (official SDK) and `deepseek` / `groq` (OpenAI-compatible) | T-001 | `launch_agents/llm/anthropic_provider.py`<br>`launch_agents/llm/openai_compat.py`<br>`tests/test_llm_anthropic.py`<br>`tests/test_llm_openai_compat.py`<br>`evidence/T-025/`<br>`prs/T-025.md` | todo |
| [T-026](T-026-accounts-signup-login-sessions-and-password-reset.md) | Accounts: sign-up, login, sessions, email verification and password reset | T-001 | `launch_agents/accounts/`<br>`launch_agents/persistence/accounts.py`<br>`tests/test_auth.py`<br>`tests/test_accounts_repository.py`<br>`evidence/T-026/`<br>`prs/T-026.md` | todo |
| [T-027](T-027-team-memberships-invites-and-access-policy.md) | Team: memberships, co-founder invites and the access policy for every company | T-001 | `launch_agents/team/`<br>`launch_agents/access/`<br>`launch_agents/persistence/team.py`<br>`tests/test_team.py`<br>`tests/test_access_policy.py`<br>`evidence/T-027/`<br>`prs/T-027.md` | todo |
| [T-028](T-028-transactional-email-templates-outbox-and-smtp.md) | Transactional email: templates, outbox delivery and the SMTP sender | T-001 | `launch_agents/email/`<br>`launch_agents/adapters/smtp_email.py`<br>`launch_agents/persistence/email_outbox.py`<br>`tests/test_email_templates.py`<br>`tests/test_email_outbox.py`<br>`evidence/T-028/`<br>`prs/T-028.md` | todo |
| [T-029](T-029-billing-plans-stripe-checkout-portal-and-webhooks.md) | Billing: plans, Stripe Checkout and customer portal, webhooks and entitlements | T-001 | `launch_agents/billing/`<br>`launch_agents/adapters/stripe_payments.py`<br>`launch_agents/persistence/billing.py`<br>`tests/test_billing.py`<br>`tests/test_stripe_adapter.py`<br>`evidence/T-029/`<br>`prs/T-029.md` | todo |
| [T-030](T-030-background-jobs-runner-worker-and-scheduler.md) | Background jobs: database queue, worker with retries, scheduler and CLI | T-001 | `launch_agents/jobs/`<br>`launch_agents/persistence/jobs.py`<br>`tests/test_jobs.py`<br>`evidence/T-030/`<br>`prs/T-030.md` | todo |
| [T-031](T-031-signed-pdf-and-word-document-rendering.md) | Signed PDF and editable Word rendering of founding documents | T-001 | `launch_agents/pdf/`<br>`tests/test_pdf.py`<br>`evidence/T-031/`<br>`prs/T-031.md` | todo |
| [T-032](T-032-security-csrf-headers-rate-limits-usage-limits-and-pii.md) | Security: CSRF, security headers, rate limits, per-account AI usage limits and the sensitive-data scrubber | T-001 | `launch_agents/security/`<br>`launch_agents/persistence/limits.py`<br>`tests/test_security.py`<br>`tests/test_rate_limits.py`<br>`tests/test_metering.py`<br>`tests/test_pii.py`<br>`evidence/T-032/`<br>`prs/T-032.md` | todo |
| [T-033](T-033-observability-structured-logs-request-ids-and-error-reporting.md) | Observability: structured logs, request ids, redaction and pluggable error reporting | T-001 | `launch_agents/observability/`<br>`tests/test_observability.py`<br>`evidence/T-033/`<br>`prs/T-033.md` | todo |
| [T-047](T-047-keelstart-brand-and-support-wording-in-foundation.md) | Foundation follow-up: the Keelstart brand and support wording without reply times | T-001 | `launch_agents/domain/constants.py`<br>`launch_agents/domain/billing.py`<br>`.env.example`<br>`tests/test_foundation.py`<br>`evidence/T-047/`<br>`prs/T-047.md` | todo |

## Wave 2

The services that join it all up: the Manager conversation with hand-overs, the website build-check-publish pipeline, the company and legal services with electronic signatures, signature and 83(b) reminder emails, data export and account deletion, and the admin service.

| Ticket | Title | Depends on | Owns | Status |
|---|---|---|---|---|
| [T-012](T-012-manager-agent-and-turn-graph.md) | Manager Agent and the LangGraph turn graph (routing, handoffs, fact gathering) | T-001, T-002, T-006, T-007, T-008, T-010 | `launch_agents/agents/manager/`<br>`launch_agents/orchestrator/`<br>`tests/test_manager_agent.py`<br>`tests/test_orchestrator.py`<br>`evidence/T-012/`<br>`prs/T-012.md` | todo |
| [T-013](T-013-website-pipeline-and-service.md) | Website pipeline and service: build, QA, automatic fixes and deploy gate, as tracked jobs | T-001, T-005, T-008, T-009, T-030 | `launch_agents/pipelines/`<br>`launch_agents/workflows/website.py`<br>`tests/test_website_pipeline.py`<br>`tests/test_website_service.py`<br>`evidence/T-013/`<br>`prs/T-013.md` | todo |
| [T-014](T-014-case-service-conversation-and-progress.md) | Case service: companies per account, conversations, action execution, names, checklist and progress | T-001, T-002, T-005, T-007, T-010, T-027, T-032 | `launch_agents/workflows/case.py`<br>`tests/test_case_service.py`<br>`evidence/T-014/`<br>`prs/T-014.md` | todo |
| [T-015](T-015-legal-service-cap-table-documents-signoff.md) | Legal service: cap table, document generation, electronic signatures, signed downloads and audit trail | T-001, T-002, T-003, T-004, T-005, T-006, T-026, T-027, T-031, T-047 | `launch_agents/workflows/legal.py`<br>`tests/test_legal_service.py`<br>`evidence/T-015/`<br>`prs/T-015.md` | todo |
| [T-035](T-035-notifications-and-83b-deadline-reminders.md) | Notifications and 83(b) deadline reminders | T-005, T-026, T-027, T-028, T-030 | `launch_agents/notifications/`<br>`tests/test_notifications.py`<br>`tests/test_reminders.py`<br>`evidence/T-035/`<br>`prs/T-035.md` | todo |
| [T-037](T-037-privacy-data-export-and-account-deletion.md) | Privacy: export all my data and delete my account | T-003, T-005, T-026, T-027, T-029, T-031, T-047 | `launch_agents/privacy/`<br>`launch_agents/persistence/privacy.py`<br>`tests/test_privacy.py`<br>`evidence/T-037/`<br>`prs/T-037.md` | todo |
| [T-038](T-038-admin-service-and-admin-cli.md) | Admin service and CLI: customers, companies, plans, AI usage, failed jobs and emails | T-005, T-026, T-027, T-028, T-029, T-030, T-032 | `launch_agents/admin/`<br>`launch_agents/persistence/admin.py`<br>`tests/test_admin.py`<br>`evidence/T-038/`<br>`prs/T-038.md` | todo |

## Wave 3

The complete, secured backend: every endpoint checks who you are and what you may do; sign-up, billing, team, chat, legal and website all work over the API; ready-made demo companies at every stage.

| Ticket | Title | Depends on | Owns | Status |
|---|---|---|---|---|
| [T-016](T-016-api-core-composition-and-demo-seed.md) | Composition root, secured app factory, health and readiness, and demo seeding | T-012, T-013, T-014, T-015, T-024, T-025, T-026, T-027, T-028, T-029, T-030, T-032, T-033, T-035, T-037, T-038, T-047 | `launch_agents/composition.py`<br>`launch_agents/api/__init__.py`<br>`launch_agents/api/app.py`<br>`launch_agents/api/errors.py`<br>`launch_agents/api/deps.py`<br>`launch_agents/api/middleware.py`<br>`launch_agents/api/schemas.py`<br>`launch_agents/api/routes/__init__.py`<br>`launch_agents/demo/`<br>`tests/test_composition.py`<br>`tests/test_api_app.py`<br>`tests/test_api_routes_contract.py`<br>`tests/test_demo_seed.py`<br>`evidence/T-016/`<br>`prs/T-016.md` | todo |
| [T-017](T-017-api-legal-cap-table-and-website-routes.md) | HTTP API: cap table, documents and e-signatures, signed downloads, audit, and website jobs | T-005, T-013, T-015, T-027, T-031, T-032 | `launch_agents/api/routes/legal.py`<br>`launch_agents/api/routes/website.py`<br>`tests/test_api_legal.py`<br>`tests/test_api_website.py`<br>`evidence/T-017/`<br>`prs/T-017.md` | todo |
| [T-039](T-039-api-auth-account-team-and-privacy-routes.md) | HTTP API: sign-up, login, sessions, account settings, data export and deletion, team and invites | T-026, T-027, T-032, T-037 | `launch_agents/api/routes/auth.py`<br>`launch_agents/api/routes/account.py`<br>`launch_agents/api/routes/team.py`<br>`tests/test_api_auth.py`<br>`tests/test_api_account.py`<br>`tests/test_api_team.py`<br>`evidence/T-039/`<br>`prs/T-039.md` | todo |
| [T-040](T-040-api-billing-webhook-and-admin-routes.md) | HTTP API: plans, Stripe checkout and portal, webhook, test checkout, and the admin endpoints | T-029, T-030, T-032, T-038 | `launch_agents/api/routes/billing.py`<br>`launch_agents/api/routes/admin.py`<br>`tests/test_api_billing.py`<br>`tests/test_api_admin.py`<br>`evidence/T-040/`<br>`prs/T-040.md` | todo |
| [T-041](T-041-api-companies-chat-names-guide-and-jobs-routes.md) | HTTP API: companies, chat, names, registration guide and job status | T-012, T-014, T-027, T-030, T-032 | `launch_agents/api/routes/cases.py`<br>`launch_agents/api/routes/jobs.py`<br>`tests/test_api_cases.py`<br>`tests/test_api_jobs.py`<br>`evidence/T-041/`<br>`prs/T-041.md` | todo |

## Wave 4

Every screen: the Keelstart landing page and pricing with Free, Launch and Team, sign-up and onboarding, chat and overview, names and domains, legal e-signing, cap table, website, registration guide, settings with billing and team, and the admin area, each checked in a real browser; plus Docker with PostgreSQL and automatic checks on every change.

| Ticket | Title | Depends on | Owns | Status |
|---|---|---|---|---|
| [T-018](T-018-chat-and-overview-screens.md) | Chat experience and Overview screen | T-011, T-016, T-039, T-041 | `frontend/src/features/chat/`<br>`frontend/src/features/overview/`<br>`evidence/T-018/`<br>`prs/T-018.md` | todo |
| [T-019](T-019-names-domains-and-registration-guide-screens.md) | Names & Domains screen and Registration Guide checklist | T-011, T-016, T-039, T-041 | `frontend/src/features/names/`<br>`frontend/src/features/guide/`<br>`evidence/T-019/`<br>`prs/T-019.md` | todo |
| [T-020](T-020-legal-signoff-and-audit-screens.md) | Legal documents with electronic signatures, signed downloads, and the Audit trail | T-011, T-016, T-017, T-039 | `frontend/src/features/legal/`<br>`frontend/src/features/audit/`<br>`evidence/T-020/`<br>`prs/T-020.md` | todo |
| [T-021](T-021-cap-table-screen.md) | Cap Table screen: table, ownership chart, vesting timeline, downloads | T-011, T-016, T-017, T-039 | `frontend/src/features/cap-table/`<br>`evidence/T-021/`<br>`prs/T-021.md` | todo |
| [T-022](T-022-website-preview-qa-and-deploy-screen.md) | Website screen: live preview, QA report, deploy status and download | T-011, T-016, T-017, T-039, T-041 | `frontend/src/features/website/`<br>`evidence/T-022/`<br>`prs/T-022.md` | todo |
| [T-034](T-034-docker-compose-ci-and-operations-guide.md) | Deployment: Docker image, compose with PostgreSQL and worker, GitHub Actions CI, operations guide | T-005, T-016, T-030, T-033 | `Dockerfile`<br>`docker-compose.yml`<br>`.dockerignore`<br>`.github/`<br>`docs/operations.md`<br>`tests/test_deploy_files.py`<br>`evidence/T-034/`<br>`prs/T-034.md` | todo |
| [T-036](T-036-onboarding-flow-and-companies-list.md) | Onboarding flow and companies list: describe your company, meet your agents, start | T-011, T-016, T-039, T-041 | `frontend/src/features/onboarding/`<br>`evidence/T-036/`<br>`prs/T-036.md` | todo |
| [T-042](T-042-auth-screens-signup-login-verify-reset-and-invite.md) | Auth screens: sign up, log in, verify email, reset password, accept a co-founder invite | T-011, T-016, T-039 | `frontend/src/features/auth/`<br>`evidence/T-042/`<br>`prs/T-042.md` | todo |
| [T-043](T-043-marketing-pricing-and-legal-pages.md) | Public pages: landing, pricing, Terms of Service, Privacy Policy, disclaimer and security | T-011, T-016, T-040 | `frontend/src/features/marketing/`<br>`evidence/T-043/`<br>`prs/T-043.md` | todo |
| [T-044](T-044-settings-team-billing-and-privacy-screens.md) | Settings and team: profile, security, billing and plan, data export and deletion, co-founders and invites | T-011, T-016, T-039, T-040 | `frontend/src/features/settings/`<br>`frontend/src/features/team/`<br>`evidence/T-044/`<br>`prs/T-044.md` | todo |
| [T-045](T-045-admin-area-screens.md) | Admin area screens: customers, companies, AI usage, failed jobs, emails and system status | T-011, T-016, T-040 | `frontend/src/features/admin/`<br>`evidence/T-045/`<br>`prs/T-045.md` | todo |

## Wave 5

The whole customer journey, from the landing page and payment to a finished company kit, tested end to end, plus a plain guide to running the product.

| Ticket | Title | Depends on | Owns | Status |
|---|---|---|---|---|
| [T-023](T-023-end-to-end-founder-journey.md) | End-to-end customer journey: API test suite, browser journey and the run guide | T-018, T-019, T-020, T-021, T-022, T-034, T-036, T-042, T-043, T-044, T-045 | `tests/test_e2e_journey.py`<br>`tests/test_e2e_security.py`<br>`docs/running-the-app.md`<br>`evidence/T-023/`<br>`prs/T-023.md` | todo |

## Wave 6

The demo video: one command records every agent at work, in reliable mode (identical every run) or live mode (real AI, real domain checks, real publishing).

| Ticket | Title | Depends on | Owns | Status |
|---|---|---|---|---|
| [T-046](T-046-demo-video-reliable-and-live.md) | Demo video: one-command scripted recording of every agent, in reliable and live modes | T-023 | `demo/`<br>`tests/test_demo_video.py`<br>`evidence/T-046/`<br>`prs/T-046.md` | todo |

## Open questions for the product owner

Each has a default already applied in the plan; confirm or change it.

| Id | Ticket | Question | Recommended |
|---|---|---|---|
| Q-010 | T-043 | Should the landing-page tagline change now that the product is called Keelstart? | Keep the current tagline |

## Answered

| Id | Question | Answer |
|---|---|---|
| Q-001 | Who needs to approve each founder's 83(b) tax election form? | Only that founder |
| Q-002 | Which hosting service should publish the founder's website? | Netlify |
| Q-003 | Can a founder still edit a document after every founder has approved it? | Yes, everyone re-approves |
| Q-004 | When does founder vesting start? | On the incorporation date |
| Q-005 | Which pages should the website have when the founder doesn't say? | Home, About, Services, Contact |
| Q-006 | How should founders pay for the product, and how much? | Three tiers: Free, Launch $29/month, Team $79/month ([ADR-0038](../docs/adr/0038-plans-v2-free-launch-team-and-plan-settings.md)) |
| Q-007 | What should the product be called? | Charterly ([ADR-0039](../docs/adr/0039-brand-charterly-everywhere-customers-look.md)); later renamed **Keelstart** by the owner ([ADR-0041](../docs/adr/0041-brand-keelstart-everywhere-customers-look.md)) |
| Q-008 | When a founder deletes their account, what happens to a company they share with co-founders? | Company stays with co-founders |
| Q-009 | What reply times should the pricing page promise for support on each plan? | No promised times: "Email support" on every plan, "Priority support" on Team ([ADR-0042](../docs/adr/0042-support-wording-no-promised-reply-times.md)) |
