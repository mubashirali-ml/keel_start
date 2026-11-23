# T-012: Manager Agent and the LangGraph turn graph (routing, handoffs, fact gathering)

| | |
|---|---|
| **Wave** | 2 |
| **Depends on** | T-001, T-002, T-006, T-007, T-008, T-010 |
| **ADRs** | [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0010](../docs/adr/0010-llm-provider-abstraction-and-fake.md), [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md), [ADR-0007](../docs/adr/0007-stack-and-module-layout.md) |
| **Status** | todo |

## Goal

A founder's chat message goes to the Manager, which gathers and validates the case facts
(asking follow-up questions), brings in the right specialist with a visible handover,
takes the conversation back when the specialist is done, and locks the facts when the
founder confirms the summary.

## Owns (only these paths may change)

- `launch_agents/agents/manager/`
- `launch_agents/orchestrator/`
- `tests/test_manager_agent.py`
- `tests/test_orchestrator.py`
- `evidence/T-012/`
- `prs/T-012.md`

## Contracts

- **Provides:** `handle_turn(turn: TurnInput, deps: AgentDeps) -> TurnResult` and `build_graph(deps)` (ADR-0009 turn steps 1–6); `ManagerAgent`; `ManagerExtraction{facts: FactsPatch, confirms_summary: bool}`; `RouteDecision{target: AgentId, reason: str}`; `next_question(result: ValidationResult) -> ChatMessage`; `facts_summary(facts) -> str`; `FAKE_HANDLERS` for `manager.extract`, `manager.route`, `manager.reply`. Keeps `manager_greeting()` from T-001.
- **Consumes:** `validate_facts` (T-002), `LawAgent` (T-006), `NameAgent` (T-007), `WebsiteAgent` (T-008), `GuideAgent` (T-010), `apply_patch`, `handoff_message`, `LockFacts` (T-001).
- **LLM context keys:** `manager.extract` -> `{"text", "facts": CaseFacts json, "pending_fact"}`; `manager.route` -> `{"text", "active_agent", "routable": [ids], "facts_complete": bool}`; `manager.reply` -> `{"text", "facts_summary"}`.

## Acceptance criteria

1. The graph is a compiled LangGraph `StateGraph` with nodes extract -> validate -> route -> handover -> respond -> hand_back; at most one specialist runs and at most two handoff messages are emitted per turn (tested).
2. Routing: a legal question goes to Law, a naming question to Name, a website request to Website, a filing question to Guide (handover message "Manager brought in the …" spoken by the Manager, then the specialist's messages); a follow-up while a specialist is active and still on topic stays with it (no handoff); a change of topic emits a return then a new handover; `@law` etc. force the target; non-routable targets (qa, cap_table, signoff) fall back to the Manager.
3. Fact gathering: facts stated anywhere in a message are merged every turn; the Manager asks for missing facts one at a time in the ADR-0013 order and records `pending_fact`; validation issues are explained first (e.g. "Equity adds up to 90%…") as a `validation` message with the issue payload; the default-vesting note is said once per founder (`notices_given`).
4. Confirmation: with complete valid facts the Manager shows `facts_summary` and asks to confirm (suggested replies "Yes, that's right" / "I need to change something"); a confirmation returns `LockFacts`; a fact change after locking unlocks and says documents will be refreshed after re-confirmation.
5. Specialist `hand_back=True` produces a return handoff and `active_agent = manager`; every agent message has the correct `agent`.
6. Memory across turns: a six-turn conversation test builds facts incrementally from `TurnInput.history`/`facts` and never asks again for a fact already given.
7. Any `LLMOutputError` gives a friendly Manager message and leaves facts unchanged; `handle_turn` never raises for LLM failures.
8. Fake handlers are deterministic and documented in `fake.py`: `manager.extract` parses entity ("LLC", "C-Corp"/"corporation"), state names or codes, founders written as `Name <email> 60%` or `Name (email) 60%`, "N months vesting" / "N-month cliff" per founder, ISO dates for incorporation, "we are building …"/"our business …" for the description, "call it …"/"names like …" for preferences, website asks ("a Pricing page", "include testimonials", contact email/phone); `manager.route` is keyword-based with the active agent as tie-breaker.

## Feature run (`evidence/T-012/feature_run.py`)

Runs a scripted multi-turn conversation through `handle_turn` with `FakeLLM` and
`FakeDomainChecker`, carrying facts/state/history between turns like the service will:
business description -> entity + state -> founders with 60/30 equity (validation issue
shown) -> corrected to 60/40 (default vesting note for Bob) -> incorporation date ->
"LLC or C-Corp?" (handover to Law) -> "suggest names" (return + handover to Name) ->
"pick the first one" (ChooseName + return to Manager) -> "yes, that's right" (LockFacts).
Prints every message as `[agent] kind: content` and asserts the handoff sequence, the
actions and the final facts.

## Out of scope

Persisting anything or executing actions (T-014); website building (T-013).
