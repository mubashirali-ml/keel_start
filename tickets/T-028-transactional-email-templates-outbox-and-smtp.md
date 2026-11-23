# T-028: Transactional email: templates, outbox delivery and the SMTP sender

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0039](../docs/adr/0039-brand-charterly-everywhere-customers-look.md), [ADR-0029](../docs/adr/0029-transactional-email-notifications-and-83b-reminders.md), [ADR-0028](../docs/adr/0028-background-jobs-queue-worker-and-scheduler.md), [ADR-0023](../docs/adr/0023-reliability-timeouts-retries-and-failure-states.md), [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md), [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md) |
| **Status** | todo |

## Goal

Every transactional email (verify email, password reset, co-founder invite, signature
needed, document executed, 83(b) reminder) looks like it comes from a real product, in
plain text and HTML, and is delivered reliably: stored first, sent by a job with retries,
never sent twice for the same event, and printed to the console in development.

## Owns (only these paths may change)

- `launch_agents/email/`
- `launch_agents/adapters/smtp_email.py`
- `launch_agents/persistence/email_outbox.py`
- `tests/test_email_templates.py`
- `tests/test_email_outbox.py`
- `evidence/T-028/`
- `prs/T-028.md`

## Contracts

- **Provides:** `render_email`, `TEMPLATE_DATA_KEYS`, `OutboxMailer` (implements `Mailer`), `send_outbox_email` (the `email.send` job handler), `ConsoleEmailSender`, `FileDropEmailSender(path)`, `SmtpEmailSender(settings, *, smtp_factory=None)`, `EmailOutboxRepository`, `OutboxEmail` (ADR-0029).
- **Consumes:** `EmailTemplate`, `EmailMessage`, `SendResult`, `EmailSender`, `FakeEmailSender`, `JobRunner`, `InlineJobRunner`, `RetryableJobError`, `tables.py`, `Settings` (`brand_name`, `app_base_url`, SMTP fields) (T-001).

## Acceptance criteria

1. `render_email` produces subject, text and HTML for all six templates with the ADR-0029 data keys; missing keys raise `KeyError`; every value is HTML-escaped (a `<script>` founder name renders as text); links only from `APP_BASE_URL`; brand name in subject prefix (`Charterly: `), header (word mark as text) and footer (ADR-0039); when `EMAIL_FROM` has no display name the From header reads `Charterly <address>`; footer explains why the email was sent; legal-content emails carry the not-legal-advice line.
2. Snapshot-style tests keep the six rendered emails (text parts) stable; HTML has no remote images, scripts or external CSS.
3. No template accepts or prints a document body, share counts, tax ids or addresses (the data-key allow-list enforces it).
4. `OutboxMailer.send` stores the row and enqueues `email.send` (5 attempts); the same `dedupe_key` twice stores and sends once and returns None the second time.
5. `send_outbox_email`: success -> row `sent` with provider id; transient failure -> `RetryableJobError` (job retried); permanent failure -> row `failed` with the error; an already-sent row is not resent (idempotent).
6. `SmtpEmailSender` (tested with an injected fake `smtplib.SMTP` factory): STARTTLS when configured, login when credentials exist, 10 s timeout, multipart/alternative message with both parts and `From: EMAIL_FROM`; connection errors and 4xx replies -> `transient=True`; 5xx -> permanent; never raises.
7. `ConsoleEmailSender` logs recipient (masked), subject and the first link; never the HTML body. `FileDropEmailSender` appends one JSON line per message (to, subject, text, html, template) and is safe for concurrent writers; after a successful send the bodies of `verify_email`, `password_reset` and `invite_cofounder` rows are replaced by `[sent]`.
8. Repository methods tested on real SQLite.

## Feature run (`evidence/T-028/feature_run.py`)

Renders all six templates with sample data and prints each subject and text body; with
`InlineJobRunner`, a temp SQLite outbox and a `FakeEmailSender` set to fail twice
transiently, sends a signature-needed email (prints the attempts and the final `sent`
row), sends it again with the same dedupe key (nothing sent), sends one to a permanently
failing sender (row `failed`), and shows the console sender's log line.

## Out of scope

Deciding when to send (T-026, T-027, T-035), the worker (T-030), email screens.
