# T-035: Notifications and 83(b) deadline reminders

| | |
|---|---|
| **Wave** | 2 |
| **Depends on** | T-005, T-026, T-027, T-028, T-030 |
| **ADRs** | [ADR-0029](../docs/adr/0029-transactional-email-notifications-and-83b-reminders.md), [ADR-0028](../docs/adr/0028-background-jobs-queue-worker-and-scheduler.md), [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0016](../docs/adr/0016-registration-guide-data-and-checklist.md) |
| **Status** | todo |

## Goal

Founders never miss what needs them: they get an email when their signature is needed
and when a document is signed by everyone, and 83(b) reminders 14, 7 and 2 days before
the deadline (once each, never a burst), until they mark the election as mailed.

## Owns (only these paths may change)

- `launch_agents/notifications/`
- `tests/test_notifications.py`
- `tests/test_reminders.py`
- `evidence/T-035/`
- `prs/T-035.md`

## Contracts

- **Provides:** `EmailNotifier(repo, team, accounts, mailer, settings)` implementing `Notifier`; `ReminderSweep(repo, team, accounts, mailer, *, today)` with `run(job=None, ctx=None) -> dict` (the `reminders.sweep` handler); `register_notification_jobs(registry, sweep)` (ADR-0029).
- **Consumes:** `Repository` (T-005), `TeamRepository` (T-027), `AccountsRepository` (T-026), `OutboxMailer` / `RecordingMailer` (T-028 / T-001), `JobRegistry` (T-001), `deadline_83b`, `days_until` (T-001), the guide step id `83b-mail` (ADR-0016).

## Acceptance criteria

1. `signatures_needed` emails each listed founder: their account email when a member is linked, else the founder's email from the facts with a sign-up link; data keys per ADR-0029; dedupe `sig:{document_id}:{version}:{founder_id}` (calling twice sends once).
2. `document_executed` emails every member once per document version.
3. Reminder sweep over companies with locked facts and an incorporation date, per founder whose `83b-mail` step is unticked: on day 14, 7 and 2 before the deadline one email each; if the sweep did not run for a while, only the smallest due threshold is sent (e.g. first run at 5 days left sends the 7-day reminder, not 14 and 7); nothing after the deadline; nothing once `83b-mail` is ticked; dedupe `83b:{case_id}:{founder_id}:{threshold}` makes reruns safe.
4. The sweep returns counts (`companies`, `founders`, `sent`, `skipped`) and never fails the whole run because of one company (errors are logged and counted).
5. No email contains share counts, document bodies or tax ids (asserted on the mailer's recorded data).
6. Tests use a temp SQLite database, `RecordingMailer` and an injected `today`, walking through 30 days.

## Feature run (`evidence/T-035/feature_run.py`)

Creates a company with Alice and Bob (incorporated 2026-12-01, deadline 2026-12-31),
drafts a document and calls `signatures_needed` twice (one email each), executes it
(two emails), then runs the reminder sweep for every day from 2026-12-10 to 2027-01-02,
ticking Alice's `83b-mail` step on 2026-12-26; prints each day's emails (recipient masked,
template, days left) and the final counts.

## Out of scope

Templates and delivery (T-028), the scheduler (T-030), calling the notifier from the legal service (T-015).
