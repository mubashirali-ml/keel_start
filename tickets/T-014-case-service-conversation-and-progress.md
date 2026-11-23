# T-014: Case service: conversations, action execution, names, checklist and progress

| | |
|---|---|
| **Wave** | 2 |
| **Depends on** | T-001, T-002, T-005, T-007, T-010 |
| **ADRs** | [ADR-0017](../docs/adr/0017-services-and-http-api-surface.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0012](../docs/adr/0012-persistence-and-data-model.md), [ADR-0016](../docs/adr/0016-registration-guide-data-and-checklist.md), [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md) |
| **Status** | todo |

## Goal

One service runs a founder's case end to end: it starts a case with the Manager's
greeting, stores every message, runs each turn, carries out what the agents asked for
(lock facts, choose a name, draft documents, build or deploy the site), keeps the
registration checklist, and reports progress across all steps with the 83(b) countdown.

## Owns (only these paths may change)

- `launch_agents/workflows/case.py`
- `tests/test_case_service.py`
- `evidence/T-014/`
- `prs/T-014.md`

## Contracts

- **Provides:** `CaseService` exactly per ADR-0017 (constructor and all methods, progress rules).
- **Consumes:** `Repository` (T-005), `validate_facts` (T-002), `check_candidate` (T-007, for `recheck_names` and unknown names in `choose_name`), `build_guide` (T-010), `manager_greeting`, `TurnHandler`/`TurnInput`/`AgentDeps`, `LegalServicePort`, `WebsiteServicePort` (T-001). The real turn handler (T-012) and the real legal/website services (T-015, T-013) are built in parallel: tests inject fakes written in this test file.

## Acceptance criteria

1. `create_case` stores a case and the greeting; `get_view` returns a `CaseView` with all ADR-0017 fields; `list_cases` newest first with percent.
2. `post_message`: stores the founder message (with `founder_id`), passes the last 20 messages as history, saves the returned facts/state, stores agent messages in order, and returns founder + new messages, the updated view and the last `open_view`.
3. Actions run in order: `LockFacts` (lock, `facts_locked_at`, `facts_locked` audit; regenerates documents through `legal.generate_documents` when documents already exist), `ChooseName` (sets `company_name` and `chosen_domain`, `name_chosen` audit), `DraftDocuments`, `BuildWebsite`, `DeployWebsite` (their returned messages are stored after the agent's messages). A `LaunchError` from an action becomes a friendly message from the requesting agent, never an exception.
4. `choose_name` via the API path works without chat and also posts a Name Agent confirmation message; `recheck_names` re-checks every candidate through the domain checker and saves them.
5. `get_guide` builds the guide from facts, chosen domain and the latest deployed URL, merges saved ticks and counts done/total; `set_guide_item` saves the tick, audits `checklist_updated`, and rejects unknown item ids with `NotFoundError`.
6. Progress follows every ADR-0017 rule, including website "packaged" when deploy is not configured and legal `attention` when the 83(b) deadline is less than 8 days away (or passed) and not every 83(b) is executed; `days_until_83b` uses the injected `today`.
7. Facts, messages and state persist: a new `CaseService` on the same repository continues the conversation.

## Feature run (`evidence/T-014/feature_run.py`)

With a temp SQLite repository, a small scripted turn handler (defined in the feature run)
that returns specific messages and actions, and recording fakes for the legal and website
ports: creates a case (prints greeting), posts four founder messages that lead to
`LockFacts`, `ChooseName`, `DraftDocuments`, `BuildWebsite`; prints the stored messages
with agents, the action calls the fakes received, and the progress after each step; ticks
two checklist items and prints the guide progress and the 83(b) countdown.

## Out of scope

The Manager logic (T-012), legal and website internals (T-015, T-013), HTTP (T-016).
