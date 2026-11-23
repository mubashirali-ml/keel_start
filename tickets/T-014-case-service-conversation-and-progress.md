# T-014: Case service: companies per account, conversations, action execution, names, checklist and progress

| | |
|---|---|
| **Wave** | 2 |
| **Depends on** | T-001, T-002, T-005, T-007, T-010, T-027, T-032 |
| **ADRs** | [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0033](../docs/adr/0033-security-hardening.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0028](../docs/adr/0028-background-jobs-queue-worker-and-scheduler.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0016](../docs/adr/0016-registration-guide-data-and-checklist.md), [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md) |
| **Status** | todo |

## Goal

One service runs each company end to end for its members: a founder creates a company
(becoming its owner), sees only their own companies, chats with the agents (with tax ids
removed before anything is stored or sent), and the service carries out what the agents
ask for (lock facts, choose a name, draft documents, start website jobs), keeps the
registration checklist and reports progress with the 83(b) countdown.

## Owns (only these paths may change)

- `launch_agents/workflows/case.py`
- `tests/test_case_service.py`
- `evidence/T-014/`
- `prs/T-014.md`

## Contracts

- **Provides:** `CaseService` exactly per ADR-0032 (constructor and every method, progress rules of ADR-0017 kept, the new `CaseView` fields).
- **Consumes:** `Repository` (T-005), `TeamService` (T-027: `add_owner`, `link_founder`), `scrub` (T-032), `validate_facts` (T-002), `check_candidate` (T-007), `build_guide` (T-010), `manager_greeting`, `TurnHandler`/`TurnInput`/`AgentDeps`, `LegalServicePort`, `WebsiteServicePort`, `JobRunner`/`InlineJobRunner`, `EntitlementsProvider`/`StaticEntitlements`, `CaseAccess` (T-001). The real turn handler (T-012) and legal/website services (T-015, T-013) are built in parallel: tests inject fakes written in this test file.

## Acceptance criteria

1. `create_case(ctx)`: requires a user; stores the company with `created_by` and `billing_user_id`, the OWNER membership and the greeting; beyond the plan's `max_companies` -> `PlanRequiredError` ("Your plan includes 1 company. Upgrade to add more.").
2. `list_cases(ctx)` returns only companies the user is a member of, newest first, with percent; `get_view(access)` fills every `CaseView` field incl. `my_role`, `my_founder_id`, `plan`, `active_jobs`.
3. `post_message(access, text)` (`CHAT`): scrubs the text first (the stored founder message and the turn input contain only the scrubbed text; when something was removed, a Manager `notice` explains it once per message); stores the founder message with `founder_id = access.founder_id`; runs the turn with `agent_deps(access)`; saves facts/state; stores agent messages; executes actions in order; returns founder + new messages, the view, `open_view` and any started `jobs`.
4. Actions: `LockFacts` (lock, audit with the actor, then `legal.regenerate_if_drafted`; link the owner's membership to the founder whose email equals the owner's email when not linked yet), `ChooseName`, `DraftDocuments` (`legal.generate_documents`), `BuildWebsite` / `DeployWebsite` (`website.request_build` / `request_deploy`, returning jobs; the agent's message says the work has started). A `LaunchError` from an action (incl. `PlanRequiredError`) becomes a friendly message from the requesting agent with a suggested reply "See plans", never an exception.
5. A `UsageLimitError` raised during the turn leaves facts and state unchanged, stores the founder message and a Manager notice with the allowance message (ADR-0033).
6. `choose_name`, `recheck_names`, `get_guide`, `set_guide_item` (`TICK_GUIDE`, audited with the actor), `delete_case` (`DELETE_COMPANY`) work as specified; unknown checklist ids -> `NotFoundError`.
7. Progress rules of ADR-0017 including "packaged" websites and the 83(b) attention rule with the injected `today`.
8. Persistence across a new `CaseService` on the same repository.

## Feature run (`evidence/T-014/feature_run.py`)

With a temp SQLite repository, a scripted turn handler, recording legal/website fakes,
`InlineJobRunner`, the real `TeamService` and Launch entitlements: Alice creates a company
(prints the greeting and her membership); posts four messages leading to `LockFacts`
(owner linked to f1), `ChooseName`, `DraftDocuments`, `BuildWebsite` (job printed); posts a
message containing an SSN and prints the stored, scrubbed text and the notice; prints
progress after each step; ticks two checklist items; shows that a second user without
membership cannot list the company, and that a Free-plan user cannot create a second one.

## Out of scope

The Manager logic (T-012), legal and website internals (T-015, T-013), authorization itself (T-027), HTTP (T-041).
