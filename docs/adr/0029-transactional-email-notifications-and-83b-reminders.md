# ADR-0029: Transactional email, notifications and 83(b) reminders

| | |
|---|---|
| **Status** | Accepted; email branding in [ADR-0039](0039-brand-charterly-everywhere-customers-look.md) |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor, product owner |
| **Tickets** | T-001 (types, ports, fakes), T-028 (templates, outbox, SMTP), T-035 (notifier, reminder sweep), T-026/T-027/T-015 (senders) |
| **Scope** | `domain/email.py`, `ports/email.py`, `ports/notifications.py`, `launch_agents/email/`, `adapters/smtp_email.py`, `persistence/email_outbox.py`, `launch_agents/notifications/` |

## Context

The brief: transactional emails for verify email, invite co-founder, "your signature is
needed", "document executed", password reset, and 83(b) deadline reminders at 14, 7 and
2 days, through an email-provider port with a fake for tests. Emails must never be lost
on a transient provider error, never be sent twice for the same event, and never carry
sensitive data.

## Decision

### Contracts (T-001)

```python
class EmailTemplate(str, Enum):
    VERIFY_EMAIL = "verify_email"; PASSWORD_RESET = "password_reset"
    INVITE_COFOUNDER = "invite_cofounder"; SIGNATURE_NEEDED = "signature_needed"
    DOCUMENT_EXECUTED = "document_executed"; DEADLINE_83B_REMINDER = "deadline_83b_reminder"
class EmailMessage(BaseModel):
    to: str; subject: str; text: str; html: str; template: EmailTemplate
class SendResult(BaseModel):
    ok: bool; provider_id: str | None = None; error: str | None = None; transient: bool = False
class EmailSender(Protocol):            # transport; never raises for provider errors
    name: str
    def send(self, message: EmailMessage) -> SendResult: ...
class FakeEmailSender:                  # name "fake"; .sent list; fail_next(n, transient=True)
class Mailer(Protocol):                 # what services call
    def send(self, template: EmailTemplate, to: str, data: Mapping[str, Any], *,
             user_id: str | None = None, case_id: str | None = None,
             dedupe_key: str | None = None) -> str | None: ...   # outbox id, or None when deduplicated
class RecordingMailer:                  # fake Mailer: .sent list of (template, to, data, dedupe_key); honours dedupe
class Notifier(Protocol):               # what LegalService calls (ports/notifications.py)
    def signatures_needed(self, case_id: str, document: Document, founder_ids: Sequence[str]) -> None: ...
    def document_executed(self, case_id: str, document: Document) -> None: ...
class RecordingNotifier:                # fake; .events list
```

### Templates (`email/templates.py`, T-028)

```python
def render_email(template: EmailTemplate, data: Mapping[str, Any], *, brand_name: str,
                 base_url: str) -> EmailMessage
TEMPLATE_DATA_KEYS: Mapping[EmailTemplate, frozenset[str]]
```

| Template | Data keys | Subject (brand prefix) |
|---|---|---|
| verify_email | `full_name`, `link` | Confirm your email |
| password_reset | `full_name`, `link` | Reset your password |
| invite_cofounder | `inviter_name`, `company_name`, `founder_name`, `link` | {inviter} invited you to {company} |
| signature_needed | `founder_name`, `company_name`, `document_title`, `version`, `link` | Your signature is needed: {document} |
| document_executed | `founder_name`, `company_name`, `document_title`, `link` | Signed by everyone: {document} |
| deadline_83b_reminder | `founder_name`, `company_name`, `deadline`, `days_left`, `link` | {n} days left to file your 83(b) election |

Every email has a plain-text and an HTML part (inline CSS, no remote images, brand
name and logo text, a footer with "You are receiving this because ...", the "not legal
advice" line where legal content is mentioned). Values are HTML-escaped; links are
built from `APP_BASE_URL` only. No document body, share counts, tax ids or addresses are
ever put in an email. `string.Template` with `html.escape`; missing keys raise
`KeyError` in tests (no silent blanks).

### Delivery (`email/outbox.py`, T-028)

```python
class OutboxMailer:                     # implements Mailer
    def __init__(self, outbox: EmailOutboxRepository, jobs: JobRunner, settings: Settings) -> None
def send_outbox_email(job: JobRecord, ctx: JobContext, *, outbox: EmailOutboxRepository,
                      sender: EmailSender) -> dict                       # the email.send handler
class EmailOutboxRepository:            # persistence/email_outbox.py
    def add(self, message: EmailMessage, *, user_id, case_id, dedupe_key) -> str | None
    def get(self, outbox_id) -> OutboxEmail; def mark_sent(self, outbox_id, provider_id, *, now) -> None
    def mark_failed(self, outbox_id, error, *, now) -> None; def list_recent(self, *, status=None, limit=100) -> list[OutboxEmail]
```

`OutboxMailer.send` renders, stores the row (deduplicated by `dedupe_key`) and enqueues
`email.send` (5 attempts, backoff from ADR-0028). The handler sends through the
`EmailSender`; a transient failure raises `RetryableJobError`, a permanent one marks the
row `failed`.

Senders: `SmtpEmailSender(settings)` (stdlib `smtplib`, STARTTLS, 10 s timeout, works
with any SMTP provider such as Postmark, Amazon SES, Resend or Mailgun);
`ConsoleEmailSender` (development: logs recipient, subject and the link so the owner can
click "verify" locally); `FakeEmailSender` (tests); `FileDropEmailSender(path)` (appends
each message as one JSON line to `EMAIL_DROP_FILE`; used whenever that setting is set, so
browser-driven runs and the demo can read emails from another process; refused in
production). Selection by `EMAIL_PROVIDER` / `EMAIL_DROP_FILE` (ADR-0021).

After a successful send, the bodies of `verify_email`, `password_reset` and
`invite_cofounder` rows are replaced by `[sent]`, so no usable token stays at rest in the
outbox.

### Notifications and reminders (`notifications/`, T-035)

```python
class EmailNotifier:                    # implements Notifier
    def __init__(self, repo: Repository, team: TeamRepository, accounts: AccountsRepository,
                 mailer: Mailer, settings: Settings) -> None
class ReminderSweep:
    THRESHOLDS = (14, 7, 2)
    def __init__(self, repo: Repository, team: TeamRepository, accounts: AccountsRepository,
                 mailer: Mailer, *, today: Callable[[], date]) -> None
    def run(self, job: JobRecord | None = None, ctx: JobContext | None = None) -> dict   # reminders.sweep handler
```

- `signatures_needed`: one email per listed founder who has an account in the company
  (else to the founder's email in the facts, with a link to sign up), dedupe key
  `sig:{document_id}:{version}:{founder_id}`. Sent after drafting, after an edit (to the
  founders whose signatures were invalidated) and after a regeneration.
- `document_executed`: to every member, dedupe `exec:{document_id}:{version}:{user_id}`.
- **83(b) reminders:** daily sweep over companies with locked facts and an
  incorporation date. For each founder whose 83(b) election is not yet marked mailed
  (guide step `83b-mail` unticked), when `days_until(deadline) <= threshold` for a
  threshold not yet sent, send the reminder for the **smallest** such threshold only
  (dedupe `83b:{case_id}:{founder_id}:{threshold}`), so a missed day never produces three
  emails at once. No reminders after the deadline has passed (the Overview shows the
  overdue state instead). Reminders are sent on every plan, free included.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Outbox table + job + SMTP sender (chosen) | Never lost, never duplicated; any provider via SMTP; visible in admin | SMTP lacks provider analytics |
| B. A provider HTTP API (Postmark, Resend) | Delivery webhooks | Ties v1 to one vendor; another adapter later is easy behind the port |
| C. Send inline during the request | Simple | Lost on error; slows the request |

## Consequences

- The owner needs an SMTP account (any provider) and a verified sending domain for
  production (`EMAIL_FROM`).
- Every email path is testable with `RecordingMailer` / `FakeEmailSender`.
