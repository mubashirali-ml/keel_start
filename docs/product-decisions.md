# Product decisions

The product owner's decisions, and the defaults the Supervisor chose while waiting for one.
Each entry records the date, the question, the answer and what changed, with links.
Open questions also appear in [tickets/plan.json](../tickets/plan.json) (`open_questions`).

## Confirmed by the product owner

| Date | Question | Answer | What changed |
|---|---|---|---|
| 2026-11-23 | Should the backend be FastAPI? | Yes: FastAPI with a SQLite database, as in the product brief. | Fixed in [ADR-0007](adr/0007-stack-and-module-layout.md) (backend stack) and [ADR-0012](adr/0012-persistence-and-data-model.md) (SQLite). No plan change needed. |

## Defaults waiting for confirmation (open questions)

Each default is already in the plan. If the owner picks the other option, the Supervisor
writes a superseding ADR and updates the tickets listed.

| Id | Question | Default applied | Where it lives |
|---|---|---|---|
| Q-001 | Who needs to approve each founder's 83(b) form? | **Only that founder.** IP Assignment and Bylaws/Operating Agreement summaries need every founder. | [ADR-0014](adr/0014-founding-documents-and-signoff-state-machine.md); [T-004](../tickets/T-004-signoff-state-machine.md), [T-006](../tickets/T-006-law-agent-and-document-drafting.md), [T-015](../tickets/T-015-legal-service-cap-table-documents-signoff.md) |
| Q-002 | Which hosting service publishes the website? | **Netlify** (token in `NETLIFY_AUTH_TOKEN`; without it the site is previewed and downloadable, and the app says publishing isn't set up). | [ADR-0011](adr/0011-external-service-ports-rdap-and-hosting.md); [T-008](../tickets/T-008-website-agent-renderer-and-netlify.md), [T-016](../tickets/T-016-api-core-composition-and-demo-seed.md) |
| Q-003 | Can a document be edited after everyone approved it? | **Yes.** The edit reopens it as a new version, cancels the other approvals, and the legal step is incomplete until everyone approves again. | [ADR-0014](adr/0014-founding-documents-and-signoff-state-machine.md); [T-004](../tickets/T-004-signoff-state-machine.md), [T-020](../tickets/T-020-legal-signoff-and-audit-screens.md) |
| Q-004 | When does founder vesting start? | **On the incorporation date** (no extra question). | [ADR-0013](adr/0013-case-validation-cap-table-and-vesting-rules.md); [T-003](../tickets/T-003-cap-table-vesting-and-exports.md), [T-021](../tickets/T-021-cap-table-screen.md) |
| Q-005 | Which website pages are used when the founder doesn't say? | **Home, About, Services, Contact.** | [ADR-0008](adr/0008-shared-domain-contracts.md) (`DEFAULT_SITE_PAGES`), [ADR-0015](adr/0015-website-generation-qa-and-deploy-loop.md); [T-008](../tickets/T-008-website-agent-renderer-and-netlify.md), [T-009](../tickets/T-009-qa-agent-site-checks.md) |

## Smaller product choices the Supervisor made (tell us if you disagree)

These follow the brief closely, so they are not open questions, but they are visible to founders:

- **Several companies per install.** The start screen lists cases and can start a new one ([ADR-0019](adr/0019-frontend-design-system-and-app-layout.md)).
- **Equity accepts up to two decimals** (e.g. 33.33 / 33.33 / 33.34) ([ADR-0013](adr/0013-case-validation-cap-table-and-vesting-rules.md)).
- **The 83(b) deadline is 30 calendar days and isn't moved for weekends.** The guide tells founders to file early; the Overview warns when fewer than 8 days are left ([ADR-0013](adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0017](adr/0017-services-and-http-api-surface.md)).
- **Founders confirm a summary of their facts before documents are drafted.** If facts change afterwards, documents are redrafted as new versions and everyone approves again ([ADR-0009](adr/0009-agent-message-and-handoff-protocol.md), [ADR-0014](adr/0014-founding-documents-and-signoff-state-machine.md)).
- **Five name ideas per request**, each checked on .com, .co and .io. A registry that doesn't answer shows as "couldn't check", never as "available" ([ADR-0011](adr/0011-external-service-ports-rdap-and-hosting.md)).
- **Chat replies arrive whole, with a typing indicator** (no word-by-word streaming) ([ADR-0017](adr/0017-services-and-http-api-surface.md)).
- **First-release limits are stated in the app:** no real sign-in or e-signature (approvals are made as the founder picked in the header), not legal advice, and the app never files with the state or buys the domain.
