# ADR-0020: UI recorded runs: app launch with fakes, screenshot matrix and demo seeding

| | |
|---|---|
| **Status** | Superseded by ADR-0036 |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-011 (devtools helper), T-016 (demo seeding), T-018..T-023 (use both) |
| **Scope** | `launch_agents/devtools/`, `launch_agents/demo/`, `evidence/T-NNN/` of UI tickets |

## Context

ADR-0005 requires every UI ticket's `feature_run.py` to start the backend with fakes and
the built frontend, drive the flow with Playwright, assert on what is visible and save
screenshots at 1280px and 390px in light and dark mode. Six tickets do this; without a
shared helper each would reinvent server start-up, ports and seeding. Screens also need
a case in a realistic state (e.g. half-signed documents) to be worth looking at.

## Decision

### Helper (`launch_agents/devtools/ui_run.py`, T-011)

```python
DEMO_TODAY = date(2026, 11, 23)
@dataclass
class RunningApp: base_url: str; db_url: str; case_id: str | None
def build_frontend(*, force: bool = False) -> Path
    # npm ci when node_modules is missing/older than the lockfile, then npm run build; returns frontend/dist
@contextmanager
def running_app(*, seed_stage: str | None = None, env: Mapping[str, str] | None = None) -> Iterator[RunningApp]
    # temp dir + SQLite file; env LAUNCH_FAKE_SERVICES=1, LAUNCH_TODAY=DEMO_TODAY, LAUNCH_DB_URL=...;
    # if seed_stage: launch_agents.demo.seed_case(load_settings(env), seed_stage) BEFORE the server starts;
    # starts `python -m uvicorn launch_agents.api.app:create_app --factory` on a free port (same interpreter),
    # waits for GET /api/health (30 s timeout), yields, then terminates the process and removes the temp dir
def capture_matrix(browser: Browser, url: str, name: str, out_dir: Path, *,
                   prepare: Callable[[Page], None] | None = None) -> list[Path]
    # 4 PNGs: {name}-desktop-light, -desktop-dark, -phone-light, -phone-dark
    # desktop 1280x800, phone 390x844, device_scale_factor 1, color_scheme light/dark,
    # waits for network idle and for no [aria-busy="true"] element, then runs prepare(page)
def assert_no_horizontal_scroll(page: Page) -> None
def assert_no_raw_json(page: Page) -> None        # visible text contains no '{"' or 'Traceback'
```

The helper uses Playwright's sync API and Chromium. It never needs network except for
`npm ci`. Dark-mode screenshots rely on the `system` theme default following
`color_scheme`.

### Demo scenario (`launch_agents/demo/`, T-016)

```python
DEMO_STAGES = ("new", "facts", "names", "legal", "signed", "website", "complete")
def seed_case(settings: Settings, stage: str) -> str      # returns the case id; requires settings.fake_services
# CLI: python -m launch_agents.demo --stage legal --db sqlite:///path.db   (prints the case id)
```

`seed_case` builds real services with fakes (`build_services`) and plays a fixed founder
conversation through `CaseService.post_message` (plus `LegalService.sign` and
`set_guide_item` where a stage needs founder actions), so seeded data is exactly what a
real session produces:

| Stage | Adds (cumulative) |
|---|---|
| new | case + Manager greeting |
| facts | bakery-bookkeeping business, Wyoming LLC, founders Alice Chen 60% (48/12 stated) and Bob Diaz 40% (no vesting -> default notice), incorporation date 2026-12-01; a legal question handled by the Law Agent; facts confirmed and locked |
| names | Name Agent suggestions with fake domain checks, plus a check of the founder's own idea "Acme" (`acme.com` is in `DEFAULT_FAKE_TAKEN`, so a taken `.com` is always shown), then a suggested name chosen |
| legal | documents drafted; Alice has signed hers; Bob edited one document once (shows invalidation) |
| signed | every document executed |
| website | site requested with a "Pricing" page and a testimonials item; first draft fails QA, one fix round passes; deployed to the fake host |
| complete | every registration checklist item ticked |

### Evidence conventions for UI tickets

- Screenshots go to `evidence/T-NNN/` named `<flow>-<desktop|phone>-<light|dark>.png`,
  at least one matrix per view the ticket delivers; each PNG under 500 KB.
- The feature run prints each step and each assertion, asserts visible text (agent names,
  badges, numbers), calls `assert_no_horizontal_scroll` at phone width and
  `assert_no_raw_json`, and exits non-zero on any failure.
- It exercises at least one loading, one empty and one error state (e.g. a case id that
  does not exist, or an action rejected by the API).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Shared helper + seeding through the real services (chosen) | Every UI run is consistent; seeded states are real | Seeding depends on wave-2/3 code (UI runs that need it are wave 4+) |
| B. Inserting rows directly into SQLite | No service dependency | Easy to create impossible states |
| C. Mocked API in the browser | No backend needed | Violates ADR-0005; hides integration bugs |

## Consequences

- T-011's own run (wave 1) uses `seed_stage=None` and the `/design` gallery, since the
  case API arrives in wave 3.
- If a seed stage breaks, every UI run that uses it fails loudly, which is the point.
