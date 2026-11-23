# T-041: HTTP API: companies, chat, names, registration guide and job status

| | |
|---|---|
| **Wave** | 3 |
| **Depends on** | T-012, T-014, T-027, T-030, T-032 |
| **ADRs** | [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0033](../docs/adr/0033-security-hardening.md), [ADR-0028](../docs/adr/0028-background-jobs-queue-worker-and-scheduler.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md) |
| **Status** | todo |

## Goal

Over HTTP, a logged-in founder can create and list their companies, chat with the
Manager and the specialists, see and choose names, tick the registration checklist and
follow background jobs, with every request limited to companies they belong to.

## Owns (only these paths may change)

- `launch_agents/api/routes/cases.py`
- `launch_agents/api/routes/jobs.py`
- `tests/test_api_cases.py`
- `tests/test_api_jobs.py`
- `evidence/T-041/`
- `prs/T-041.md`

## Contracts

- **Provides:** the T-041 rows of the ADR-0032 table as `router = APIRouter()` in each file, request bodies in the same files.
- **Consumes:** `CaseService` (T-014) wired with the real `handle_turn` (T-012), `JobRunner` (T-030), `require_user` / `require_case` / `rate_limit` (T-016 `api/deps.py`, same wave: tests use a minimal app with equivalent dependencies built on `authorize_case` from T-027).

## Acceptance criteria

1. `POST /api/cases` -> 201 `CaseView` for the creator (402 `plan_required` beyond the plan's company limit); `GET /api/cases` lists only the caller's companies; `GET /api/cases/{id}` 404 for non-members; `DELETE` needs `DELETE_COMPANY`.
2. `POST /messages` (`CHAT`, `llm` rate-limit class, text 1–4,000 chars) returns the founder message plus all new messages with correct `agent` fields and handoffs, the view, `open_view` and `jobs`; the founder message's `founder_id` is the caller's founder; a body `founder_id` is rejected.
3. Conversation persists across requests and app restarts on the same DB file; two members of the same company see the same conversation; a non-member gets 404.
4. Names, choose, recheck (`llm` class), guide and guide ticks (`TICK_GUIDE`) per ADR-0032.
5. `GET /api/cases/{id}/jobs` and `/jobs/{job_id}` return only that company's jobs (404 for a job of another company).
6. A message containing an SSN is stored scrubbed and the response includes the Manager's notice; a usage-limit hit returns 200 with the Manager's allowance notice (not an error page).

## Feature run (`evidence/T-041/feature_run.py`)

Over `TestClient` with fakes on a temp DB, logged in as Alice: creates a company and plays
the founder journey (business, founders with a 90% mistake corrected, a legal question
-> Law handover, names -> Name handover, choose through `/names/choose`, confirm facts,
tick two guide items), printing each response's messages as `[agent] content`, the
progress and the 83(b) countdown; shows that Carol (another user) gets 404 for Alice's
company; requests a website build through chat and polls the job endpoint until done.

## Out of scope

Legal and website routes (T-017), auth routes (T-039), the app (T-016), UI (wave 4).
