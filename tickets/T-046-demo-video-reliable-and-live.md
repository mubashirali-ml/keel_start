# T-046: Demo video: one-command scripted recording of every agent, in reliable and live modes

| | |
|---|---|
| **Wave** | 6 |
| **Depends on** | T-023 |
| **ADRs** | [ADR-0041](../docs/adr/0041-brand-keelstart-everywhere-customers-look.md), [ADR-0037](../docs/adr/0037-demo-video-scripted-recording-reliable-and-live-modes.md), [ADR-0036](../docs/adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md), [ADR-0022](../docs/adr/0022-llm-providers-fake-claude-code-anthropic-deepseek-groq.md), [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md), [ADR-0025](../docs/adr/0025-dependency-set-v2-python-and-npm.md), [ADR-0003](../docs/adr/0003-merge-gate-tests-and-recorded-run.md) |
| **Status** | todo |

## Goal

The owner presents the product with a video produced by one command: a scripted run of
the real app at 1920x1080 that shows, with a caption for each step and at a readable
pace, what every agent produces (case summary, legal answer and the three drafted
documents, name cards with domain availability, the cap table with chart and Excel file,
e-signing with an invalidation and re-sign, the website preview with its QA report and
deploy URL or "packaged", and the registration checklist), saved as WebM and MP4 with a
screenshot per step and every artifact; identical every time in reliable mode, and with
real AI, real domain checks and a real deploy in live mode.

## Owns (only these paths may change)

- `demo/`
- `tests/test_demo_video.py`
- `evidence/T-046/`
- `prs/T-046.md`

## Contracts

- **Provides:** `demo/record_demo.py` (CLI per ADR-0037: `--mode reliable|live`, `--out`, `--pace`, `--keep-server`), `DemoStep`, `STEPS`, `run_demo`, `DemoResult`, `StepResult`, the caption overlay, the MP4 conversion, `demo/README.md` (how to run both modes, what each needs, where the output goes, how long it takes), `demo/.gitignore` (`output/`).
- **Consumes:** `running_app`, `login`, `build_frontend` (T-011), `seed_case` stage `account` (T-016), every screen (wave 4), the fake services (T-001), `imageio_ffmpeg` (ADR-0025), the `claude_code` / `anthropic` providers (T-024, T-025) in live mode.

## Acceptance criteria

1. `bash scripts/py.sh demo/record_demo.py` (reliable, default) runs offline with fake LLM, RDAP, hosting, email and payments, `DEMO_MODE=1`, `LAUNCH_TODAY`, and writes `demo/output/<UTC timestamp>/` with `demo.webm`, `demo.mp4` (H.264, yuv420p, playable), `screenshots/NN-<step>.png` for each of the nine ADR-0037 steps, `artifacts/` (documents, `cap-table.csv`, `cap-table.xlsx`, signed PDFs, website files, `qa-report.json`, `checklist.json`, `names.json`, `emails.json`, `transcript.json`) and `summary.json`.
2. Video is 1920x1080, 3–6 minutes at `--pace normal`; the video opens with a Keelstart title card (word mark and tagline, ADR-0041) and ends with an end card; every step starts with a 1-second title card and shows a caption bar (agent name in its accent color + one-sentence caption) that is legible in the screenshots.
3. Each step asserts the visible, tangible output listed in ADR-0037 before continuing (Manager summary; Law answer and 2 + one-per-founder documents; 5 name cards with Taken and Available badges; Bob joined; cap table 10,000,000 with chart and a completed Excel download; invalidation message then Executed on all documents and a downloaded signed PDF; preview, QA round failed then passed, deploy URL or "Packaged"; ticked checklist with progress; Overview end state).
4. Waits are conditions with timeouts (no fixed sleeps except the pacing holds); a failing step stops the run, keeps the partial video and screenshot, prints the step and reason, and exits non-zero.
5. Reliable mode is deterministic: two runs produce byte-identical deterministic artifacts (Markdown documents, CSV, website files, QA report, checklist, names, transcript text), the XLSX and PDFs equal by extracted content, and `summary.json` hashes match.
6. Live mode (`--mode live`): requires `LLM_PROVIDER` `claude_code` or `anthropic` (clear error otherwise) and refuses `APP_ENV=production`; uses real RDAP, Netlify only when `NETLIFY_AUTH_TOKEN` is set ("Packaged" otherwise), fake email and payments; assertions are structural; prints the provider and per-step durations. Live mode is documented and manual, not part of the gate.
7. `tests/test_demo_video.py` (no browser): step list order and captions, output-folder layout and naming, the summary schema, deterministic-artifact comparison logic, and the live-mode guards.
8. **Three consecutive passing runs:** the feature run executes the reliable demo three times in a row; all three pass and their deterministic artifacts are identical.
9. `demo/README.md` and the T-023 run guide document the one command; the operator links it from the root README (harness-owned).

## Feature run (`evidence/T-046/feature_run.py`)

Builds the frontend once, then runs `run_demo("reliable", <temp out>, pace="normal")`
three times in a row; after each run prints the step table (step, agent, PASS, duration),
the video duration and resolution read with ffmpeg from `imageio_ffmpeg`, the MP4 size
and the artifact hashes; asserts all three runs passed and that the deterministic
artifacts are identical across runs; copies the last run's screenshots (one per step,
each under 500 KB, resized if needed) into `evidence/T-046/` (videos are not committed)
and prints the folder layout of the last output.

## Out of scope

Changes to product screens or services (report `BLOCKED` with the failing step instead), hosting the video.
