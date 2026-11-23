# Product brief: Startup Incorporation & Compliance Engine

This is the input the Supervisor plans from. It describes **what** to build, not how.
Every "how" decision is the Supervisor's to make and record as an ADR in `docs/adr/`.

## Problem

Founders of a new US startup need to agree on terms (entity type, equity split, vesting,
incorporation date), get the core legal paperwork drafted, build a cap table, and have
every founder sign off. Today this takes several lawyer round-trips, and it's easy to miss
the IRS 83(b) filing deadline.

## What the product does

Founders describe their startup in a chat. The app checks the terms, drafts the legal
documents, builds the cap table, and gets every founder to sign off.

## Required capabilities

1. **Manager Agent (LLM).** Reads the founder chat and extracts the terms: company name,
   entity type (`Delaware C-Corp` or `LLC`), founders with equity %, vesting months,
   cliff months, and incorporation date.
   - Equity must add up to exactly 100%.
   - IRS 83(b) deadline = incorporation date + 30 days.
   - When something is missing or invalid, it asks follow-up questions and keeps the case
     open across several chat turns.
   - Default vesting when not stated: 48 months with a 12-month cliff (stated to the user).
   - The LLM extracts; deterministic code validates and decides.
2. **Legal Drafter (LLM).** Writes 3 Markdown documents from the locked terms:
   Founder IP Assignment Agreement, Bylaws Summary (an Operating Agreement summary for an
   LLC), and an IRS 83(b) Election Form per founder. Unknown details stay as placeholders
   such as `[ADDRESS]`. Share counts must match the cap table exactly.
3. **Cap Table Builder (deterministic).** Splits 10,000,000 authorized shares (units for
   an LLC) by equity %, always summing to exactly 10,000,000. Builds a monthly 4-year
   vesting schedule with a 1-year cliff: nothing vests before the cliff, the accrued
   portion vests at the cliff, then the rest vests monthly. Exports CSV and Excel.
4. **Multi-party sign-off (deterministic).** Each document has a version number.
   - When every founder has signed the current version, the document becomes `Executed`.
   - If someone edits it, the version goes up and the other founders' signatures are
     cancelled (the editor's signature moves to the new version).
   - Acting on a stale version must be rejected, not silently applied.
   - Every action goes into an audit log.
   - When all documents are executed, the case is ready to file.
5. **Backend:** FastAPI with a SQLite database.
6. **Demo UI:** Streamlit, with a founder switcher, an 83(b) deadline countdown, chat,
   cap table, document review and an audit trail.
7. **LLM provider:** OpenAI-compatible providers (DeepSeek primary, Groq for now), chosen
   by configuration with no code change. Tests and recorded runs must not need a paid key.

## Scope limits

- US only: Delaware C-Corp and LLC.
- Generated documents are drafts, not legal advice.
- No real authentication or e-signature in the first release (state it as a limitation).

## Definition of done for the product

- All capabilities above work end to end through the API and the UI.
- An automated test suite covers the deterministic rules and the API flows (LLM stubbed).
- Each merged change has a recorded feature run.
- Each significant design decision has an ADR.
