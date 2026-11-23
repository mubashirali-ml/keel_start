# T-007: Name Agent with live RDAP domain checks

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0010](../docs/adr/0010-llm-provider-abstraction-and-fake.md), [ADR-0011](../docs/adr/0011-external-service-ports-rdap-and-hosting.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md) |
| **Status** | todo |

## Goal

The founder gets company-name ideas that fit the business, each with an honest live
domain check for `.com`, `.co` and `.io`, the state's official name-search link and the
USPTO trademark link marked "check manually", and can pick one in the chat.

## Owns (only these paths may change)

- `launch_agents/agents/name/`
- `launch_agents/adapters/rdap.py`
- `tests/test_name_agent.py`
- `tests/test_rdap.py`
- `evidence/T-007/`
- `prs/T-007.md`

## Contracts

- **Provides:** `NameAgent` (Specialist, `AgentId.NAME`); `suggest_names(facts, llm, count=5) -> list[NameSuggestion]`; `check_candidate(suggestion, checker, state_code, now) -> NameCandidate`; `NameIntent`, `NameSuggestions` (`NameSuggestion` = `{name, rationale}`, defined in this package); `RdapDomainChecker` (ADR-0011); `FAKE_HANDLERS` for `name.intent`, `name.suggest`, `name.reply`.
- **Consumes:** `AgentContext`, `AgentReply`, `ChooseName`, `OpenView`, `DomainChecker`, `DomainCheck`, `NameCandidate`, `StateNameCheck`, `state_info`, `domain_label`, `DOMAIN_TLDS`, `USPTO_TRADEMARK_SEARCH_URL` (T-001).
- **LLM context keys:** `name.suggest` -> `{"business_description", "name_preferences", "entity_type", "count", "exclude": [names already suggested]}`; `name.intent` -> `{"text", "candidates": [names]}`; `name.reply` -> `{"text", "candidates": [{name, domains}]}`.

## Acceptance criteria

1. `check_candidate` checks `domain_label(name)` + each of `.com`, `.co`, `.io` in that order and records each status; `state_check` uses `state_info(state).name_search_url` with status `check_manually` (None when no state yet); trademark link always present.
2. `NameAgent.handle` "suggest": returns a `name_options` message with payload candidates, updates `state.name_candidates` (deduplicated by name, case-insensitive), suggested replies "Choose {name}" for candidates with at least one available domain, plus a line saying state availability must be checked manually with the link. Wording for `unknown` never says available.
3. "choose" by name or by number ("the second one") -> `ChooseName(name, domain=<first available domain or None>)`, a confirmation message, `hand_back=True`; choosing a name that is not a candidate checks it first.
4. "check" a founder-supplied name ("is Loaf Labs free?") -> checks it and adds it as a candidate.
5. `RdapDomainChecker` (tests use `httpx.MockTransport`, no network): bootstrap lookup by TLD and caching (fetched once); 200 -> taken; 404 -> available; 429/500/timeout/connection error -> unknown with a detail; rdap.org fallback for unknown TLDs; correct `Accept` header.
6. `LLMOutputError` or a checker returning unknown never crashes the agent.
7. Fake `name.suggest` is deterministic and derived from the business description and preferences (e.g. keywords combined with a fixed suffix list), never repeats `exclude`; fake `name.intent` is keyword/number based.

## Feature run (`evidence/T-007/feature_run.py`)

With `FakeLLM` and `FakeDomainChecker(taken={"crumbledger.com"})`: asks for names for the
sample bakery-bookkeeping business, prints each candidate with its three domain statuses,
the Wyoming name-search link and the USPTO link; asks to check a specific name; chooses
"the second one" and prints the `ChooseName` action. Then runs `RdapDomainChecker`
against a `MockTransport` that returns 200/404/429 and prints taken/available/unknown.

## Out of scope

Persisting the chosen name (T-014), the Names UI (T-019), state business-name APIs (none
exist for free; manual check by design).
