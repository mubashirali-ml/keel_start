# T-001: Foundation: package skeleton, shared contracts, LLM abstraction, fakes and typed stubs

| | |
|---|---|
| **Wave** | 0 |
| **Depends on** | — |
| **ADRs** | [ADR-0007](../docs/adr/0007-stack-and-module-layout.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0010](../docs/adr/0010-llm-provider-abstraction-and-fake.md), [ADR-0011](../docs/adr/0011-external-service-ports-rdap-and-hosting.md), [ADR-0012](../docs/adr/0012-persistence-and-data-model.md), [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md), [ADR-0015](../docs/adr/0015-website-generation-qa-and-deploy-loop.md), [ADR-0016](../docs/adr/0016-registration-guide-data-and-checklist.md), [ADR-0017](../docs/adr/0017-services-and-http-api-surface.md), [ADR-0020](../docs/adr/0020-ui-recorded-runs-and-demo-seeding.md) |
| **Status** | todo |

## Goal

Every later ticket can be built and tested in parallel: the whole `launch_agents/` package
exists with the shared types, the LLM provider abstraction with a deterministic fake, the
external-service ports with fakes, and exact typed stubs for every function one ticket
calls in another.

## Owns (only these paths may change)

- `launch_agents/`
- `tests/conftest.py`
- `tests/test_foundation.py`
- `pytest.ini`
- `.env.example`
- `evidence/T-001/`
- `prs/T-001.md`

## Contracts

- **Provides (implemented):**
  - `launch_agents/config.py`: `Settings`, `load_settings(env=None)` (ADR-0010 table, ADR-0011 selection defaults, `LAUNCH_TODAY`, `LAUNCH_DB_URL`, `LAUNCH_CORS_ORIGINS` comma-separated).
  - `launch_agents/domain/`: `constants.py`, `types.py` (incl. `apply_patch`, `ValidationIssue`, `ValidationResult`), `state.py`, `messages.py` (incl. `AGENT_PROFILES`, `agent_message`, `handoff_message`, `AgentAction` union), `cap_table.py`, `documents.py`, `website.py` (incl. `SiteBundle.get`, deterministic `SiteBundle.to_zip`), `guide.py`, `states.py` (`US_STATES` for 50 states + DC with https `filing_office_url` and `name_search_url`, `state_info`), `helpers.py`, `errors.py`, `views.py` — exactly per ADR-0008/0009/0013/0014/0015/0016/0017.
  - `launch_agents/llm/`: `LLMMessage`, `LLMRequest`, `LLMProvider`, `OpenAICompatibleProvider` (accepts an optional injected `chat_model` for tests), `FakeLLM`, `FakeLLMMissingHandler`, `get_llm(settings)`.
  - `launch_agents/ports/`: `DomainChecker`, `FakeDomainChecker`, `DEFAULT_FAKE_TAKEN`; `SiteHost`, `FakeSiteHost`, `UnconfiguredSiteHost`.
  - `launch_agents/agents/base.py`: `AgentServices`, `AgentContext`, `AgentReply`, `Specialist`, `TurnInput`, `TurnResult`, `AgentDeps`, `TurnHandler`.
  - `launch_agents/agents/manager/greeting.py`: `manager_greeting() -> ChatMessage` — Manager, kind `text`, fixed copy introducing the Manager and the specialists, with suggested replies ("I want to start an LLC", "Help me choose LLC or C-Corp", "Find a company name").
  - `launch_agents/workflows/ports.py`: `LegalServicePort`, `WebsiteServicePort` (ADR-0017).
  - `launch_agents/api/app.py`: skeleton `create_app(services=None, settings=None)` serving `GET /api/health` (provider names from settings; works without services), CORS, and the SPA static mount of `settings.frontend_dist` when it exists (fallback to `index.html` for non-`/api` paths). If `build_services` raises `NotImplementedError`, `app.state.services` is `None`. `api/deps.py: get_services(request)` implemented; `api/errors.py` with the error-envelope handlers (ADR-0017); `api/routes/{cases,legal,website}.py` each with an empty `router = APIRouter()`.
- **Provides (typed stubs: exact signature + docstring citing the ADR, body `raise NotImplementedError`):** `rules/validation.py` (T-002), `rules/cap_table.py` + `rules/exports.py` (T-003), `signoff/machine.py` incl. `SignOffOutcome` (T-004), `persistence/` `create_db_engine`, `init_db`, `Repository` with every method of ADR-0012 (T-005), `agents/law/` `LawAgent`, `draft_documents`, `spot_legal_issues(facts, state, today)` (T-006), `agents/name/` `NameAgent`, `suggest_names(facts, llm, count=5)`, `check_candidate(suggestion, checker, state_code, now)` and `adapters/rdap.py` `RdapDomainChecker` (T-007), `agents/website/` `WebsiteAgent`, `generate_content`, `revise_content`, `fix_content`, `render_site`, `required_pages` and `adapters/netlify.py` `NetlifySiteHost` (T-008), `agents/qa/` `deterministic_checks`, `run_qa`, `qa_summary_message` (T-009), `agents/guide/` `GuideAgent`, `build_guide` (T-010), `agents/manager/` `ManagerAgent` (T-012), `orchestrator/` `handle_turn`, `build_graph(deps)` (T-012), `pipelines/website.py` `PipelineResult`, `build_site`, `deploy_build` (T-013), `workflows/website.py` `WebsiteService`, `workflows/legal.py` `LegalService`, `workflows/case.py` `CaseService` (T-013/T-015/T-014), `composition.py` `Services` (real dataclass) + `build_services` (stub, T-016), `demo/` `DEMO_STAGES` + `seed_case` (T-016), `devtools/ui_run.py` `RunningApp`, `build_frontend`, `running_app`, `capture_matrix`, `assert_no_horizontal_scroll`, `assert_no_raw_json` (T-011).
- **Provides (fake LLM wiring):** `launch_agents/agents/{manager,law,name,website,qa,guide}/fake.py`, each `FAKE_HANDLERS: dict[str, FakeHandler] = {}`; `FakeLLM(include_defaults=True)` loads them lazily.
- **Provides (tests):** `pytest.ini` (`testpaths = tests`, `addopts = -q`), `tests/conftest.py` fixtures `fake_llm`, `fake_domain_checker`, `fake_site_host`, `today` (2026-11-23), `sample_facts` (Wyoming LLC; Alice Chen alice@example.com 60% 48/12; Bob Diaz bob@example.com 40% no vesting; incorporation 2026-12-01; business "bookkeeping software for small bakeries"), `repo` (fresh SQLite file in `tmp_path`; the fixture calls `pytest.skip` if persistence is still a stub, so it never errors at import time).
- **Consumes:** nothing.

## Acceptance criteria

1. Every module in the ADR-0007 layout imports cleanly; `tests/test_foundation.py` imports each one.
2. All domain models match the ADRs field for field (names, types, defaults, enum values) and round-trip through `model_dump(mode="json")` / `model_validate`. `ChatMessage` with `role=agent` and no `agent` is rejected.
3. `apply_patch` covers: `None` leaves values; founder matched by id, then email, then name (case-insensitive); new founders get the next free id (`f1`, `f2`, … never reused after removal); `remove_founder_ids`; `C_CORP` forces `state="DE"`; state upper-cased; `website` patch lists replace, scalars overwrite.
4. Helpers: `deadline_83b(2026-12-01) == 2026-12-31`; `add_months(2026-01-31, 1) == 2026-02-28` and leap years; `days_until` negative after the deadline; `slugify("Crumb & Co.") == "crumb-co"`; `domain_label("Crumb Ledger LLC") == "crumbledger"`.
5. `AGENT_PROFILES` matches the ADR-0009 table exactly; `handoff_message` produces the fixed wording for both directions.
6. `SiteBundle.to_zip()` is byte-identical across two calls and contains every file.
7. `US_STATES` has 51 entries, each with https URLs; `state_info("XX")` raises `InvalidStateError`.
8. `FakeLLM`: script FIFO beats registered handler beats default handler; unknown task raises `FakeLLMMissingHandler`; `complete_json` validates against the schema and raises `LLMOutputError` on invalid output; `calls` records every request.
9. `OpenAICompatibleProvider.complete_json` (with an injected `langchain_core` fake chat model, no network) parses fenced JSON, retries once on invalid JSON, then raises `LLMOutputError`.
10. `load_settings` + `get_llm` follow the ADR-0010 selection table (deepseek key -> deepseek preset; only groq key -> groq; none -> fake; `LAUNCH_FAKE_SERVICES=1` -> fake regardless; overrides honoured).
11. `FakeDomainChecker`, `FakeSiteHost`, `UnconfiguredSiteHost` behave per ADR-0011 (friendly "not configured" message).
12. Every stub exists with the exact ADR signature (checked with `inspect.signature` for parameter names; the test must NOT assert `NotImplementedError`, so it keeps passing after later tickets implement them).
13. `create_app()` with no services: `GET /api/health` returns 200 with `llm_provider`, `domain_checker`, `hosting`; a `LaunchError` raised in a route renders the ADR-0017 envelope; with a temp `frontend_dist` containing `index.html`, `GET /cases/x/overview` returns that file and `GET /api/nope` returns a JSON 404.
14. `.env.example` lists every environment variable from ADR-0010/0011 with a comment and no real secrets.
15. `bash scripts/py.sh -m pytest` passes with no network access.

## Feature run (`evidence/T-001/feature_run.py`)

Prints and asserts, without network: settings resolution for three sample env maps
(fake / deepseek / groq; keys redacted); a `FakeLLM` with a registered `demo.task`
handler answering `complete` and `complete_json` (and the `FakeLLMMissingHandler` path);
`apply_patch` merging two founder patches into `sample`-style facts; the 83(b) deadline
for 2026-12-01; a handover and a return handoff message as JSON; `FakeDomainChecker`
results for `acme.com` and `crumbledger.io`; `UnconfiguredSiteHost.deploy` message; a
two-file `SiteBundle` zip hash printed twice (equal); `GET /api/health` through FastAPI's
`TestClient`; and a list of all stub functions with their signatures.

## Out of scope

Implementing any stubbed behaviour (validation, cap table, sign-off, repository, agents,
graph, services, real API routes, frontend). No frontend files.
