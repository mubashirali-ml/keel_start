# ADR-0007: Stack and module layout

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | all (T-001 creates the layout) |
| **Scope** | `launch_agents/`, `tests/`, `pytest.ini`, `.env.example`, `frontend/` |

## Context

The brief fixes the platform: a **FastAPI** backend with **SQLite**, a React + TypeScript +
Vite + Tailwind frontend, OpenAI-compatible LLM providers, and faked external services in
tests. `requirements.txt` is fixed. Twenty-plus tickets are built in parallel by builders
who see only their own ticket, so the module map and the import direction must be decided
once, up front, with one owner per path.

## Decision

### Backend stack (all from `requirements.txt`)

| Concern | Choice |
|---|---|
| HTTP API | **FastAPI** (served by `uvicorn`), app factory `launch_agents.api.app:create_app` |
| Database | **SQLite** through **SQLAlchemy 2.0** Core/ORM (ADR-0012) |
| Types and validation | **pydantic v2** models for every cross-module type (ADR-0008) |
| Manager turn graph | **LangGraph** `StateGraph`, compiled without a checkpointer; case memory lives in our own tables (ADR-0009, ADR-0012) |
| LLM calls | **langchain-openai** `ChatOpenAI` pointed at an OpenAI-compatible `base_url` (ADR-0010) |
| Outbound HTTP (RDAP, hosting) | **httpx** (sync client, explicit timeouts) (ADR-0011) |
| Excel export | **openpyxl** |
| Config | **python-dotenv** + a pydantic `Settings` model |
| Tests | **pytest**; UI evidence with **Playwright** (ADR-0005, ADR-0020) |

No other Python package may be imported. Standard library only otherwise (`html.parser`,
`zipfile`, `csv`, `decimal`, `datetime`, `json`, `re`, `uuid`).

### Python package layout

One importable package `launch_agents/` at the repository root (`scripts/py.sh` puts the
checkout on `PYTHONPATH`; no `pyproject.toml` install step).

```
launch_agents/
  __init__.py
  config.py              Settings, load_settings()                                  T-001
  domain/                shared types, constants, helpers, errors, views (ADR-0008)  T-001
  llm/                   LLMProvider, OpenAICompatibleProvider, FakeLLM (ADR-0010)   T-001
  ports/                 DomainChecker / SiteHost protocols + fakes (ADR-0011)       T-001
  adapters/rdap.py       live RDAP DomainChecker                                     T-007
  adapters/netlify.py    live Netlify SiteHost                                       T-008
  rules/validation.py    case validation, vesting defaults, missing facts (ADR-0013) T-002
  rules/cap_table.py     share allocation and vesting schedule (ADR-0013)            T-003
  rules/exports.py       CSV and Excel export of the cap table                       T-003
  signoff/               document sign-off state machine (ADR-0014)                  T-004
  persistence/           engine, tables, Repository (ADR-0012)                       T-005
  agents/base.py         Specialist protocol, AgentContext, AgentReply (ADR-0009)    T-001
  agents/law/            Law Agent + document drafting                               T-006
  agents/name/           Name Agent                                                  T-007
  agents/website/        Website Agent + static site renderer                        T-008
  agents/qa/             QA Agent                                                    T-009
  agents/guide/          Registration Guide Agent + curated state data (ADR-0016)    T-010
  agents/manager/        Manager Agent                                               T-012
  orchestrator/          LangGraph turn graph, handle_turn() (ADR-0009)              T-012
  pipelines/website.py   build -> QA -> fix (max 2) -> deploy gate (ADR-0015)        T-013
  workflows/ports.py     service protocols used across workflows                     T-001
  workflows/website.py   WebsiteService                                              T-013
  workflows/case.py      CaseService                                                 T-014
  workflows/legal.py     LegalService                                                T-015
  composition.py         build_services(settings) composition root                   T-016
  api/                   FastAPI app, error mapping, routes (ADR-0017)               T-016, T-017
  demo/                  demo scenario + seeding for recorded runs (ADR-0020)        T-016
  devtools/              Playwright/app-launch helpers for UI recorded runs          T-011
```

Each agent package exposes its public functions from `__init__.py` and has a `fake.py`
with `FAKE_HANDLERS` for the deterministic fake LLM (ADR-0010).

**T-001 creates every file above** with the exact signatures from the ADRs and
docstrings; functions owned by later tickets raise `NotImplementedError`. A later ticket
then owns and replaces those files. Tests that need another ticket's not-yet-merged code
use dependency injection or a fake, never the stub.

### Import direction (a reviewer checks it)

```
domain  <-  llm, ports  <-  rules, signoff, persistence, agents/*  <-  orchestrator, pipelines
        <-  workflows  <-  composition  <-  api, demo
```

- `domain` imports nothing from the package.
- Agents never import `persistence`, `workflows` or `api`; they get everything through
  `AgentContext` and return `AgentReply` (ADR-0009).
- Only `composition.py` chooses concrete providers/adapters from `Settings`.
- Nothing imports `api`.

### Tests

- All Python tests live in `tests/`, one file per area named in the owning ticket
  (`tests/test_<area>.py`). `pytest.ini` sets `testpaths = tests` (so `evidence/` and
  `frontend/` are never collected).
- `tests/conftest.py` and `pytest.ini` belong to T-001 only. Shared fixtures there:
  `fake_llm`, `fake_domain_checker`, `fake_site_host`, `repo` (fresh SQLite in a tmp
  dir, created only once T-005 exists; fixtures must not fail at import time if a
  module is still a stub), `sample_facts` (two founders, Wyoming LLC), `today`
  (`date(2026, 11, 23)`).
- No test touches the network. `httpx` calls are tested with `httpx.MockTransport`.

### Running

```
bash scripts/py.sh -m uvicorn launch_agents.api.app:create_app --factory --port 8000
cd frontend && npm run dev        # Vite on 5173, proxies /api to 8000
```

When `frontend/dist/` exists, the FastAPI app also serves it at `/` (ADR-0017), so one
process serves the whole product for recorded runs.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. One package, layered modules, one owner per path (chosen) | Parallel tickets never collide; import rules are checkable | Needs a large wave-0 stub set |
| B. Separate `backend/` service packages per agent | Strong isolation | Packaging overhead; cross-package typing harder |
| C. LangGraph checkpointer as the source of truth for case memory | Built-in persistence | State opaque to the API/UI; harder to test; schema tied to the library |

## Consequences

- Builders know exactly where their code goes and what they may import.
- T-001 is large but mechanical: types, fakes and stubs.
- The FastAPI + SQLite backend is fixed; changing it needs a superseding ADR.
