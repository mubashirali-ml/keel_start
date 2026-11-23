# T-016: HTTP API core, composition root and demo seeding

| | |
|---|---|
| **Wave** | 3 |
| **Depends on** | T-012, T-013, T-014, T-015 |
| **ADRs** | [ADR-0017](../docs/adr/0017-services-and-http-api-surface.md), [ADR-0020](../docs/adr/0020-ui-recorded-runs-and-demo-seeding.md), [ADR-0010](../docs/adr/0010-llm-provider-abstraction-and-fake.md), [ADR-0011](../docs/adr/0011-external-service-ports-rdap-and-hosting.md), [ADR-0007](../docs/adr/0007-stack-and-module-layout.md) |
| **Status** | todo |

## Goal

The FastAPI backend runs the real product: configuration picks the LLM provider, domain
checker and hosting with no code change, and founders can create cases, chat, see the
case view, choose names and tick the checklist over HTTP. A one-command demo seed puts a
case in any stage of the journey for recorded runs.

## Owns (only these paths may change)

- `launch_agents/api/__init__.py`
- `launch_agents/api/app.py`
- `launch_agents/api/errors.py`
- `launch_agents/api/deps.py`
- `launch_agents/api/schemas.py`
- `launch_agents/api/routes/__init__.py`
- `launch_agents/api/routes/cases.py`
- `launch_agents/composition.py`
- `launch_agents/demo/`
- `tests/test_api_cases.py`
- `tests/test_composition.py`
- `tests/test_demo_seed.py`
- `evidence/T-016/`
- `prs/T-016.md`

## Contracts

- **Provides:** `build_services(settings) -> Services` (ADR-0017/0011 selection); full `create_app(services=None, settings=None)`; the T-016 rows of the ADR-0017 endpoint table in `routes/cases.py`; request bodies in `api/schemas.py`; `seed_case(settings, stage)`, `DEMO_STAGES`, `python -m launch_agents.demo` (ADR-0020).
- **Consumes:** `handle_turn` (T-012), `WebsiteService` (T-013), `CaseService` (T-014), `LegalService` (T-015), `Repository` (T-005), `get_llm`, ports and adapters (T-001, T-007, T-008). Includes T-017's `routes/legal.py` and `routes/website.py` routers (empty until T-017 merges; same wave).

## Acceptance criteria

1. `build_services`: `LAUNCH_FAKE_SERVICES=1` -> FakeLLM + fake checker + fake host (an explicit `HOSTING_PROVIDER` still wins for hosting, ADR-0011); DeepSeek/Groq selected by env per ADR-0010 (constructed, never called in tests); `HOSTING_PROVIDER` / `NETLIFY_AUTH_TOKEN` per ADR-0011; `DOMAIN_CHECKER=rdap` -> `RdapDomainChecker`; DB initialised at `db_url`.
2. Every T-016 endpoint in ADR-0017 works through `TestClient` with fakes, returns the ADR view shapes (a test compares response keys with the pydantic views), uses 201 for case creation and 404 envelope for unknown cases.
3. `POST /messages` returns the founder message plus all new messages with correct `agent` fields and handoff messages; the conversation persists across requests and app restarts on the same DB file.
4. Errors: `LaunchError` -> envelope with code/status; invalid body -> 422 `invalid_request` with a friendly message; unexpected exception -> 500 `internal` with the generic friendly message and no stack trace.
5. `GET /api/health` reports provider names and whether hosting is configured; secrets never appear in any response or log line.
6. Static serving and SPA fallback from T-001 still work; CORS allows the configured origins.
7. `seed_case` produces each ADR-0020 stage through the real services with fakes (asserted: stage `facts` locked; `names` has a chosen name and the founder-checked "Acme" with `acme.com` taken; `legal` has partial signatures and one invalidation; `signed` all executed; `website` deployed to the fake host after one QA fix round; `complete` all checklist items ticked); the CLI prints the case id; refuses to run unless fake services are on.

## Feature run (`evidence/T-016/feature_run.py`)

Starts the app in-process with `TestClient` and `LAUNCH_FAKE_SERVICES=1` on a temp DB and
plays the founder journey over HTTP: create case -> describe the business -> give
founders (with a 90% equity mistake corrected) -> ask a legal question (Law handover) ->
ask for names (Name handover), choose one through `/names/choose` -> confirm facts ->
tick two guide items; prints each response's messages as `[agent] content`, the case
progress and the 83(b) countdown; then seeds every demo stage with `seed_case` and prints
each stage's progress percent.

## Out of scope

Legal/cap-table/website routes (T-017), UI (wave 4).
