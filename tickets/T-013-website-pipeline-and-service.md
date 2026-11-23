# T-013: Website pipeline and service: build, QA, automatic fixes and deploy gate, as tracked jobs

| | |
|---|---|
| **Wave** | 2 |
| **Depends on** | T-001, T-005, T-008, T-009, T-030 |
| **ADRs** | [ADR-0038](../docs/adr/0038-plans-v2-free-launch-team-and-plan-settings.md), [ADR-0015](../docs/adr/0015-website-generation-qa-and-deploy-loop.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0028](../docs/adr/0028-background-jobs-queue-worker-and-scheduler.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0011](../docs/adr/0011-external-service-ports-rdap-and-hosting.md), [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md) |
| **Status** | todo |

## Goal

A website request starts a tracked job that produces a saved build QA has checked, with
up to two automatic fix rounds, chat messages from the Website and QA agents, a preview
and a zip download; publishing is a second job that only deploys after QA passes or the
founder explicitly accepts the remaining issues, and only on a plan that includes publishing.

## Owns (only these paths may change)

- `launch_agents/pipelines/`
- `launch_agents/workflows/website.py`
- `tests/test_website_pipeline.py`
- `tests/test_website_service.py`
- `evidence/T-013/`
- `prs/T-013.md`

## Contracts

- **Provides:** `PipelineResult`, `build_site(...)`, `deploy_build(...)` (ADR-0015); `WebsiteService(repo, llm_for: Callable[[str], LLMProvider], host, jobs, *, clock=utcnow)` implementing `WebsiteServicePort` (ADR-0032): `request_build`, `request_deploy`, `run_build`, `run_deploy`, `latest`, `preview_file`, `download_zip`; `register_website_jobs(registry, service)` registering the `website.build` / `website.deploy` handlers.
- **Consumes:** T-008 (`generate_content`, `revise_content`, `fix_content`, `render_site`), T-009 (`run_qa`, `qa_summary_message`), `Repository` (T-005), `JobRunner`, `InlineJobRunner`, `DbJobRunner` (T-030, used in one integration test), `CaseAccess`, `Actor`, `Permission`, `Feature`, `SiteHost` fakes, errors (T-001). `llm_for(case_id)` returns the (metered) LLM for that company; tests pass a function returning `FakeLLM`.

## Acceptance criteria

1. Pipeline rules unchanged from ADR-0015: a failing first draft (default fake) is fixed in round 1 (two reports); a never-passing draft stops after `MAX_QA_FIX_ROUNDS` (three reports); a change request revises the previous content and creates a new build version.
2. `request_build` checks `BUILD_WEBSITE`, raises `NameNotChosenError` without a company name, and enqueues `website.build` (payload: case id, change request, actor) returning the `JobRecord`; a second request while one is queued/running for the same company returns the running job (dedupe key).
3. `run_build` (the handler) saves the `SiteBuild` (version n+1), audits `site_built` with the actor, and posts in order: Website Agent `site_preview`, one QA Agent `qa_report` per round, and a closing Website Agent message (passed: "ready to publish"; failed: lists issues and asks for an explicit OK); its job result holds the build id and QA outcome.
4. `request_deploy` checks `DEPLOY` and `require_feature(WEBSITE_DEPLOY)` (Free -> `PlanRequiredError` "Publishing your website is included in the Launch and Team plans.", details `required_plan: "launch"` (ADR-0038)), raises `DeployBlockedError` on a failed build without `override_qa`, and enqueues `website.deploy`.
5. `run_deploy`: `FakeSiteHost` -> `deployed` with URL, `site_deployed` audit, `deploy_status` message; `UnconfiguredSiteHost` -> `deploy_not_configured` ("packaged"), the message says publishing is not set up and preview/download still work; host failure -> `deploy_failed` with a friendly message; override sets `override_by` to the actor's founder and audits `deploy_override`.
6. An `LLMOutputError` during a build makes the job fail with a friendly error, posts a friendly Website Agent message and saves no broken build; a `UsageLimitError` does the same with the allowance message.
7. `preview_file`, `download_zip`, `latest` require `VIEW` and only serve this company's builds (`NotFoundError` otherwise).
8. With `InlineJobRunner` the whole flow is synchronous in tests; one integration test runs the same flow through `DbJobRunner` + `Worker.run_once` on SQLite.

## Feature run (`evidence/T-013/feature_run.py`)

Temp SQLite repository, `FakeLLM`, `FakeSiteHost`, `InlineJobRunner`, a member
`CaseAccess` on Launch: builds (prints the job and both QA reports), tries to deploy a
scripted always-failing build (blocked), then with override (deployed, audit printed);
builds "add a Pricing page" and deploys normally; repeats with `UnconfiguredSiteHost`
("packaged"); shows the Free-plan deploy refusal; then runs one build through
`DbJobRunner` and a `Worker` and prints the job's status transitions.

## Out of scope

HTTP routes (T-017), the Website screen (T-022), running actions from chat (T-014).
