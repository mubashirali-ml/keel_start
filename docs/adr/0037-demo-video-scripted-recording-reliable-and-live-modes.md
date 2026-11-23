# ADR-0037: Demo video: scripted browser recording in reliable and live modes

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor, product owner |
| **Tickets** | T-046 (implements); uses T-011 helper, T-016 seeding, every screen ticket |
| **Scope** | `demo/`, `tests/test_demo_video.py`, `evidence/T-046/` |

## Context

The owner will present the product with a video (brief, "Demo video"). It must be a
first-class, reliable feature: every agent produces visible, tangible output (not just
chat text), the real React UI is driven step by step with captions at a readable pace
at 1920x1080, and each run leaves a folder with the video (WebM and MP4), a screenshot
per step and every artifact the agents produced. Two modes: `reliable` (fake LLM, fake
RDAP/hosting/email/payments, seeded data, identical every run, offline) and `live`
(`claude_code` or `anthropic`, real RDAP, real deploy when a hosting token is set).

## Decision

### One command

```
bash scripts/py.sh demo/record_demo.py                 # reliable (default)
bash scripts/py.sh demo/record_demo.py --mode live     # live: needs LLM_PROVIDER=claude_code or anthropic
           [--out demo/output] [--pace normal|fast] [--keep-server]
```

Documented in `demo/README.md` and in `docs/running-the-app.md` (T-023). The root
`README.md` is harness-owned; the owner brief asks the operator to link it.

### Script structure (`demo/`, T-046)

```python
@dataclass(frozen=True)
class DemoStep:
    id: str                       # "01-manager", "02-law", ...
    agent: str                    # caption title, e.g. "Manager Agent"
    caption: str                  # what it is doing, one sentence
    run: Callable[[DemoContext], None]     # drives the UI and asserts what is visible
    artifacts: Callable[[DemoContext], list[Path]] = lambda ctx: []
STEPS: list[DemoStep]
def run_demo(mode: Literal["reliable", "live"], out_root: Path, *, pace: str = "normal") -> DemoResult
class DemoResult(BaseModel):
    out_dir: Path; video_webm: Path; video_mp4: Path; steps: list[StepResult]; passed: bool
```

- Starts the app with `running_app` (ADR-0036): reliable = `LAUNCH_FAKE_SERVICES=1`,
  `DEMO_MODE=1`, seed stage `account` (Alice and Bob exist; Bob gets invited during the
  video); live = the operator's environment with `DEMO_MODE=1`, fake email and payments,
  `DOMAIN_CHECKER=rdap`, `HOSTING_PROVIDER=netlify` only if a token is set.
  Live mode refuses to start when `APP_ENV=production` or when the provider is not
  `claude_code` or `anthropic`.
- Playwright Chromium, viewport and `record_video_size` **1920x1080**, light theme,
  `device_scale_factor=1`. Typing uses a per-character delay; after each step's result
  appears the script holds the frame (pace `normal`: 2.5 s; `fast` for development only).
- **Captions** are an overlay the script injects into the page (a fixed bottom bar with
  the agent's name, icon color and the caption, fading between steps), not part of the
  product UI. Each step also gets a 1-second title card at the start.
- The founder switch for sign-off uses the demo-mode "Acting as" switcher (ADR-0035).

### Steps (each asserts visible output before moving on)

| # | Agent | Caption / what is shown | Assertions | Artifacts |
|---|---|---|---|---|
| 1 | Manager | Alice logs in, starts a company, first message; follow-up questions; equity typo corrected; case summary confirmed | Manager labels, validation message, summary card, facts locked | `transcript-01.json` |
| 2 | Law Agent | legal question answered in chat; "draft the documents"; the Legal view lists the three document kinds (IP assignment, operating agreement summary, one 83(b) per founder) | Law Agent label + handover banner; 4 documents; not-legal-advice notice | `documents/*.md` |
| 3 | Name Agent | name cards with availability badges for .com/.co/.io, a taken `.com`, Alice picks one | 5 cards, at least one "Taken" and one "Available" badge, chosen name in header | `names.json` |
| 4 | Team | Alice invites Bob (email in the fake outbox), Bob accepts | Bob listed as member, linked to his founder | `emails.json` |
| 5 | Cap Table | table, ownership chart, vesting timeline, Excel download | total 10,000,000 units; chart visible; download completed | `cap-table.csv`, `cap-table.xlsx` |
| 6 | Sign-off | Alice e-signs; Bob edits one document (Alice's signature invalidated, shown clearly); both re-sign; Executed; signed PDF downloaded | status badges, invalidation message, "Executed" on all | `signed/*.pdf` |
| 7 | Website + QA | site generated, preview frame, QA report with a failed check fixed automatically, deploy URL (or "Packaged" without a token) | preview visible; QA round 1 failed -> round 2 passed; URL or "Packaged" | `website/` files, `qa-report.json` |
| 8 | Registration Guide | Wyoming checklist, items ticked, progress | progress bar > 0, ticked items | `checklist.json` |
| 9 | Overview | 6 steps done, 83(b) countdown | 100 % or the expected end state | `transcript.json` (whole chat) |

In live mode the assertions are structural (labels, counts, statuses), not exact text,
and the QA step accepts "passed first time" with an adapted caption.

### Output (`demo/output/<UTC timestamp>/`, git-ignored by `demo/.gitignore`)

`demo.webm` (Playwright), `demo.mp4` (H.264, `yuv420p`, converted with the ffmpeg binary
from `imageio_ffmpeg.get_ffmpeg_exe()`), `screenshots/NN-<step>.png` (one per step, at
the step's final frame), `artifacts/` (everything in the table), and `summary.json`
(mode, provider, steps with PASS/FAIL and durations, video duration, artifact hashes).
A failed step stops the run, keeps the partial video and screenshot, and exits non-zero
with the step and the reason.

### Reliability requirements

- Reliable mode is **offline and deterministic**: fake services, `LAUNCH_TODAY`, fixed
  seed data, fixed typing; the deterministic artifacts (`*.md`, `*.csv`, website files,
  `qa-report.json`, `checklist.json`, `names.json`, transcript text) are byte-identical
  across runs (the XLSX and PDF are compared by their extracted content).
- Every wait is a condition (visible text, `aria-busy` cleared, job finished) with a
  timeout; no fixed sleeps except the pacing holds.
- Video length in reliable/normal pace: 3–6 minutes.
- The reliable demo is T-046's recorded feature run, so the merge gate runs it; the
  acceptance criteria require **three consecutive passing runs** with identical
  deterministic artifacts.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Playwright drives the real UI, injected captions, seeded fakes (chosen) | Shows the real product; repeatable; runs in the gate | Long-ish feature run (three demo runs) |
| B. Screen-record a person clicking | Natural | Not repeatable; drifts with every change |
| C. Captions built into the app | Simple overlay | Demo-only UI in the product |

## Consequences

- Any regression in a screen breaks the demo in the gate, which is the point.
- The owner can record a fresh video from any merged `main` with one command.
