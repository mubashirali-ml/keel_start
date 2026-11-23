# T-009: QA Agent: requirement and quality checks for generated websites

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0015](../docs/adr/0015-website-generation-qa-and-deploy-loop.md), [ADR-0010](../docs/adr/0010-llm-provider-abstraction-and-fake.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md) |
| **Status** | todo |

## Goal

Every website build can be checked against what the founder asked for and basic quality
rules, producing a pass/fail report with a clear issue list that the founder can read
and the Website Agent can fix.

## Owns (only these paths may change)

- `launch_agents/agents/qa/`
- `tests/test_qa_agent.py`
- `evidence/T-009/`
- `prs/T-009.md`

## Contracts

- **Provides:** `deterministic_checks(bundle, facts) -> list[QaCheckResult]` (nine checks), `run_qa(bundle, facts, llm, *, round=0, now) -> QaReport` (all ten checks, ADR order), `qa_summary_message(report) -> ChatMessage` (agent QA, kind `qa_report`), `QaLlmReview`, `FAKE_HANDLERS` for `qa.review`.
- **Consumes:** `SiteBundle`, `QaCheckId`, `QaIssue`, `QaCheckResult`, `QaReport`, `CaseFacts`, `DEFAULT_SITE_PAGES`, `slugify` (T-001). Must not import `agents.website` (built in parallel); it re-derives required pages from `facts.website.pages` or `DEFAULT_SITE_PAGES` with the same slug rule ("Home" -> `index`).
- **LLM context keys:** `qa.review` -> `{"requirements": [str], "site_text": {path: visible text}}`.

## Acceptance criteria

1. Each deterministic check has a passing fixture and at least one failing fixture with a precise issue (page and message): missing page, missing service/extra item, wrong/missing company name in title or header, missing/wrong contact email/phone/address and mismatched `mailto:`, broken local link, `<img>` without alt / svg without label, zero or two h1 / skipped level, missing doctype/lang/title/charset/viewport or unbalanced tags, contrast below 4.5:1 (WCAG relative-luminance formula, hex and rgb() colors).
2. Parsing uses only the standard library (`html.parser`); external links are never fetched.
3. `run_qa`: `passed` is True iff no error-severity issue; `requirements_review` maps LLM issues; an `LLMOutputError` adds one warning ("Automatic requirements review was unavailable") and does not fail the report.
4. `qa_summary_message` says pass/fail, the round, the number of issues and the top three in plain words; payload per ADR-0009.
5. Fake `qa.review` is deterministic and honest: it reports a requirement only if none of its words appear in `site_text`.

## Feature run (`evidence/T-009/feature_run.py`)

Builds two small `SiteBundle`s by hand (no Website Agent): a good three-page site and a
broken one (missing Contact page, missing "testimonials", wrong email, broken link, img
without alt, two h1s, low-contrast colors). Runs `run_qa` on both with `FakeLLM`, prints
each check's pass/fail and issues, the summary message, and asserts pass vs. fail.

## Out of scope

Fixing sites (T-008), the fix loop and deploy gate (T-013), the QA report UI (T-022).
