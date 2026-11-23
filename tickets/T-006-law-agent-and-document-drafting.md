# T-006: Law Agent: legal Q&A, issue spotting and founding-document drafting

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0010](../docs/adr/0010-llm-provider-abstraction-and-fake.md), [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md), [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md) |
| **Status** | todo |

## Goal

When the Manager brings in the Law Agent, the founder gets clear explanations (LLC vs
C-Corp, state choice, liability, operating agreement basics, tax treatment, vesting, the
83(b) election) with issues spotted in their own case, and can have the founding
documents drafted from the locked facts with share counts that match the cap table.

## Owns (only these paths may change)

- `launch_agents/agents/law/`
- `tests/test_law_agent.py`
- `tests/test_law_documents.py`
- `evidence/T-006/`
- `prs/T-006.md`

## Contracts

- **Provides:** `LawAgent` (Specialist, `agent_id = AgentId.LAW`); `draft_documents(facts, cap_table, today) -> list[DraftDocument]`; `spot_legal_issues(facts, state, today) -> list[LegalIssue]`; `LawIntent`; `FAKE_HANDLERS` for `law.intent` and `law.answer`; prompts in `agents/law/prompts.py`; document templates under `agents/law/templates/`.
- **Consumes:** `AgentContext`, `AgentReply`, `DraftDocuments`, `OpenView`, `LLMProvider`, `CapTable` (passed in; never computed here), `deadline_83b`, `LEGAL_NOTICE` (T-001).
- **LLM context keys:** `law.intent` -> `{"text"}`; `law.answer` -> `{"text", "topic", "entity_type", "state", "founders": [{name, equity_percent, vesting_months, cliff_months}], "issues": [message], "deadline_83b"}`.

## Acceptance criteria

1. `spot_legal_issues` returns (codes): `unequal_vesting` (founders on different schedules), `no_cliff` (a founder with cliff 0 and vesting > 0), `name_conflict` (a candidate or chosen name whose `.com` is `taken`), `deadline_83b_soon` (<= 7 days left), `deadline_83b_passed`; each message is founder-friendly; none for the clean sample.
2. `LawAgent.handle` with a question: one `text` message from `law` that answers via `law.answer`, mentions relevant spotted issues, and ends with `LEGAL_NOTICE`; `state.legal_issues` is updated; `hand_back` False.
3. With a draft request (`law.intent` = draft) and `facts_locked` True: returns `DraftDocuments` and `OpenView("legal")`, a message saying the documents are being prepared, and `hand_back=True`. With facts not locked: no action, explains the Manager must confirm the facts first, `hand_back=True`.
4. `draft_documents` for a C-Corp returns IP Assignment, Bylaws Summary and one 83(b) per founder; for an LLC the Operating Agreement Summary instead; titles and `required_signers` per ADR-0014 (83(b): that founder only).
5. Every document starts and ends with `LEGAL_NOTICE`, uses `[COMPANY NAME]` when no name is chosen, leaves `[ADDRESS]`, `[TAXPAYER ID]`, `[FAIR MARKET VALUE PER SHARE]` placeholders, and every number of shares/units in it equals `cap_table.rows[i].shares` (test parses every integer next to "shares"/"units").
6. The 83(b) form states the transfer date (incorporation date), the filing deadline (`deadline_83b`), the founder's shares/units and vesting terms.
7. `LLMOutputError` -> a friendly apology message from `law` (still with the notice); never raises.
8. Fake handlers are deterministic: `law.intent` is keyword-based ("draft", "documents", "paperwork", "prepare" -> draft); `law.answer` returns a topic paragraph (topics: entity choice, state, liability, operating agreement, tax, vesting, 83(b), general) that uses the context facts (e.g. names the entity type and the 83(b) deadline).

## Feature run (`evidence/T-006/feature_run.py`)

With `FakeLLM` and a hand-built `CapTable` for the sample: asks three questions
("LLC or C-Corp?", "what is an 83(b)?", "is unequal vesting a problem?" with unequal
facts) and prints each reply; requests drafting with unlocked then locked facts and prints
the actions; drafts the LLC and a C-Corp document set and prints each title, signers and
the first lines, asserting share counts match the cap table and the notice is present.

## Out of scope

Storing documents and signatures (T-015), the sign-off machine (T-004), routing (T-012).
