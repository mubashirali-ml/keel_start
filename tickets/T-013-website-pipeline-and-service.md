# T-013: Website pipeline and service: build, QA, automatic fixes, deploy gate

| | |
|---|---|
| **Wave** | 2 |
| **Depends on** | T-001, T-005, T-008, T-009 |
| **ADRs** | [ADR-0015](../docs/adr/0015-website-generation-qa-and-deploy-loop.md), [ADR-0017](../docs/adr/0017-services-and-http-api-surface.md), [ADR-0011](../docs/adr/0011-external-service-ports-rdap-and-hosting.md), [ADR-0012](../docs/adr/0012-persistence-and-data-model.md), [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md) |
| **Status** | todo |

## Goal

A website request produces a saved build that QA has checked, with up to two automatic
fix rounds, chat messages from the Website and QA agents, a preview and a zip download,
and a live deploy that only happens after QA passes or the founder explicitly accepts
the remaining issues.

## Owns (only these paths may change)

- `launch_agents/pipelines/`
- `launch_agents/workflows/website.py`
- `tests/test_website_pipeline.py`
- `tests/test_website_service.py`
- `evidence/T-013/`
- `prs/T-013.md`

## Contracts

- **Provides:** `PipelineResult`, `build_site(...)`, `deploy_build(...)` (ADR-0015); `WebsiteService(repo, llm, host, *, clock=utcnow)` implementing `WebsiteServicePort` (ADR-0017).
- **Consumes:** `generate_content`, `revise_content`, `fix_content`, `render_site` (T-008); `run_qa`, `qa_summary_message` (T-009); `Repository` (T-005); `SiteHost`, `FakeSiteHost`, `UnconfiguredSiteHost`, `DeployBlockedError`, `NameNotChosenError`, `slugify` (T-001).

## Acceptance criteria

1. `build_site` with a first draft that fails QA (default fake: missing extra content) fixes it in round 1 and passes: `reports` has two reports (rounds 0 and 1), `fix_rounds == 1`.
2. A draft that never passes (scripted fake) stops after exactly `MAX_QA_FIX_ROUNDS` fixes (three reports), `passed == False`.
3. A change request revises the previous content and goes through QA again as a new build version.
4. `WebsiteService.build` raises `NameNotChosenError` without a company name; otherwise saves a `SiteBuild` (version n+1), audits `site_built`, and returns messages in order: Website Agent `site_preview`, one QA Agent `qa_report` per round, and a closing Website Agent message (passed: "ready to deploy"; failed: lists issues and asks for an explicit OK).
5. `deploy` on a passed build: `FakeSiteHost` -> status `deployed` with URL, `site_deployed` audit, `deploy_status` message with the URL; `UnconfiguredSiteHost` -> `deploy_not_configured`, message says deploy is not configured and the preview/download still work; host failure -> `deploy_failed` with a friendly message.
6. `deploy` on a failed build without override raises `DeployBlockedError`; with `override_qa=True` and a founder id it deploys, sets `override_by` and audits `deploy_override` with the founder id.
7. `preview_file` serves any bundle file of the latest build (`NotFoundError` otherwise); `download_zip` returns `bundle.to_zip()` of the latest build; `latest` returns None for a case without builds.
8. An `LLMOutputError` during build returns a friendly Website Agent message and saves no broken build.

## Feature run (`evidence/T-013/feature_run.py`)

Uses a temp SQLite repository, `FakeLLM` and `FakeSiteHost`: creates a case with the
sample facts and company name "Crumb Ledger" and extra content "testimonials"; builds
(prints both QA reports, showing the fix round); tries to deploy a scripted
always-failing build (blocked), then with override (deployed, audit printed); builds a
change request "add a Pricing page" and deploys normally; repeats a deploy with
`UnconfiguredSiteHost` and prints the not-configured message; prints the zip size and the
messages for each step.

## Out of scope

HTTP routes (T-017), the Website screen (T-022), executing chat actions (T-014).
