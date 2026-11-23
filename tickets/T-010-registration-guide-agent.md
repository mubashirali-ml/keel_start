# T-010: Registration Guide Agent with curated Delaware and Wyoming data

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0016](../docs/adr/0016-registration-guide-data-and-checklist.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0010](../docs/adr/0010-llm-provider-abstraction-and-fake.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md) |
| **Status** | todo |

## Goal

The founder gets a step-by-step, state-specific registration checklist (full guides for
Delaware and Wyoming, a generic one elsewhere) including EIN, 83(b) timing, ongoing
obligations and how to buy and connect the chosen domain, with official links and a
"last reviewed" date, and can ask the Guide Agent about any step.

## Owns (only these paths may change)

- `launch_agents/agents/guide/`
- `tests/test_guide_agent.py`
- `evidence/T-010/`
- `prs/T-010.md`

## Contracts

- **Provides:** `build_guide(facts, *, chosen_domain, deployed_url) -> RegistrationGuide`; `GuideAgent` (Specialist, `AgentId.GUIDE`); curated `agents/guide/data/states.json`; `FAKE_HANDLERS` for `guide.explain`.
- **Consumes:** `RegistrationGuide`, `GuideStep`, `GuideLink`, `state_info`, `FULL_GUIDE_STATES`, `deadline_83b`, `LEGAL_NOTICE`, `FactsNotReadyError`, `OpenView` (T-001).
- **LLM context keys:** `guide.explain` -> `{"text", "state", "entity_type", "steps": [{id, title, fee, due}]}`.

## Acceptance criteria

1. `states.json` contains full guides for DE (LLC and Delaware C-Corp) and WY (LLC) with official source links (state corporations division, IRS), filing fees as strings, and a `last_reviewed` date; a test checks every URL is https and every fee has a source.
2. `build_guide` returns steps in the ADR-0016 order with stable ids; the 83(b) step has `due = deadline_83b(incorporation_date)`; the domain step names at least three registrars, what to check, the chosen domain (or "your chosen domain") and how to connect DNS to `deployed_url` (or "once your site is live").
3. Other states (e.g. `TX`): `full_guide=False`, generic steps with that state's filing-office and name-search links and "confirm the current fee on the state site" wording.
4. Missing state or entity type -> `FactsNotReadyError` with a friendly message.
5. `disclaimer` contains `LEGAL_NOTICE` and says the app does not file anything.
6. `GuideAgent.handle` answers with `guide.explain` about the matching steps, returns `OpenView("guide")` and a `guide_ready` message the first time; without state/entity it says the Manager needs those facts and hands back.
7. Fake `guide.explain` is deterministic: it lists the titles and fees of steps whose words match the question (EIN, registered agent, annual report, domain, 83(b)), or summarises the first three steps.

## Feature run (`evidence/T-010/feature_run.py`)

Prints the full Wyoming LLC guide for the sample (chosen domain `crumbledger.io`, deployed
URL set), the Delaware C-Corp guide step titles, and a Texas generic guide; asks the Guide
Agent "how do I get an EIN?" and "how do I buy my domain?" with `FakeLLM` and prints the
replies; asserts the 83(b) due date and the `last_reviewed` date are shown.

## Out of scope

Saving checklist ticks (T-014), the checklist UI (T-019).
