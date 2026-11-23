# ADR-0036: UI recorded runs with accounts, demo mode and demo seeding v2

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-011 (devtools helper), T-016 (demo seeding), T-018..T-023, T-042..T-046 (use both) |
| **Scope** | `launch_agents/devtools/`, `launch_agents/demo/`, `evidence/T-NNN/` of UI tickets |

## Context

ADR-0020 gave UI tickets one helper to start the app with fakes, a screenshot matrix and
seeded demo stages played through the real services. With accounts, every page behind
`/app` needs a logged-in user, co-founders need their own accounts and memberships, and
signatures need e-signature evidence. This ADR **supersedes ADR-0020**; its screenshot
matrix, evidence conventions and "seed through the real services" rule carry over.

## Decision

### Helper (`launch_agents/devtools/ui_run.py`, T-011)

```python
DEMO_TODAY = date(2026, 11, 23)
DEMO_PASSWORD = "demo-password-2026"            # only ever used with fake services
@dataclass
class RunningApp:
    base_url: str; db_url: str; case_id: str | None
    users: dict[str, str]                       # "alice" -> email, "bob" -> email
    email_drop: Path                            # EMAIL_DROP_FILE of the run (ADR-0029)
    def read_emails(self, *, to: str | None = None) -> list[dict]: ...   # parsed JSON lines, oldest first
@contextmanager
def running_app(*, seed_stage: str | None = None, plan: str = "launch", demo_mode: bool = True,
                env: Mapping[str, str] | None = None) -> Iterator[RunningApp]
    # temp dir + SQLite file migrated to head; env APP_ENV=test, LAUNCH_FAKE_SERVICES=1,
    # LAUNCH_TODAY=DEMO_TODAY, DEMO_MODE=1|0, RATE_LIMITS_ENABLED=0, JOBS_EMBEDDED_WORKER=1, LAUNCH_DB_URL,
    # EMAIL_DROP_FILE=<temp>/emails.jsonl;
    # seeds BEFORE the server starts; starts uvicorn on a free port; waits for /api/ready (30 s)
def login(page: Page, app: RunningApp, who: str = "alice") -> None   # through the real login form
def build_frontend(*, force: bool = False) -> Path
def capture_matrix(browser: Browser, url: str, name: str, out_dir: Path, *,
                   prepare: Callable[[Page], None] | None = None,
                   storage_state: str | None = None) -> list[Path]      # logged-in captures reuse a storage state
def assert_no_horizontal_scroll(page: Page) -> None
def assert_no_raw_json(page: Page) -> None
```

### Demo scenario (`launch_agents/demo/`, T-016)

```python
DEMO_STAGES = ("account", "new", "facts", "names", "legal", "signed", "website", "complete")
@dataclass
class SeedResult: case_id: str | None; users: dict[str, str]
def seed_case(settings: Settings, stage: str, *, plan: PlanId = PlanId.LAUNCH) -> SeedResult
# CLI: python -m launch_agents.demo --stage legal --plan launch --db sqlite:///path.db  (prints the case id)
```

`seed_case` requires `settings.fake_services` and refuses otherwise. It builds real
services (`build_services` with `InlineJobRunner`) and acts through them, so seeded data
is exactly what real sessions produce:

| Stage | Adds (cumulative) |
|---|---|
| account | users Alice Chen (alice@example.com) and Bob Diaz (bob@example.com), both verified, password `DEMO_PASSWORD`; Alice on `plan` (fake subscription) |
| new | Alice creates a company (owner, Manager greeting) |
| facts | the ADR-0020 conversation (bakery-bookkeeping, Wyoming LLC, Alice 60% 48/12, Bob 40% default vesting, incorporation 2026-12-01, a Law Agent question), facts locked; Alice's membership linked to f1; Alice invites Bob, Bob accepts (linked to f2) |
| names | as ADR-0020 (fake suggestions, "Acme" with `acme.com` taken, a name chosen) |
| legal | documents drafted; Alice e-signs all of hers (typed name, consent, hash); Bob edits one document once and e-signs the new version (Alice's signature on it is invalidated) |
| signed | every document executed (both founders re-sign) |
| website | site with a Pricing page and a testimonials item; first draft fails QA, one fix round passes; deployed to the fake host (jobs run inline) |
| complete | every registration checklist item ticked |

### Evidence conventions

As ADR-0020: `evidence/T-NNN/<flow>-<desktop|phone>-<light|dark>.png` (< 500 KB each),
visible-text assertions, `assert_no_horizontal_scroll` at 390 px, `assert_no_raw_json`,
at least one loading, one empty and one error state. New: every UI run logs in through
the real login page at least once (no cookie injection for the first login), and a run
that shows an authorization boundary asserts that Bob cannot open a company he is not a
member of (friendly not-found page).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Seed users + memberships through the real services, log in through the UI (chosen) | Realistic; exercises auth in every UI run | Slightly slower runs |
| B. Disable auth in recorded runs | Fast | Hides the most important integration |
| C. Inject session cookies directly | Fast | Skips the login flow entirely |

## Consequences

- All UI evidence shows the product as a logged-in customer sees it.
- The demo video (ADR-0037) reuses the same seeding and helper.
