# Product brief: Startup Launch Agents (LLC formation, name, website, compliance)

This is the input the Supervisor plans from. It describes **what** to build, not how.
Every "how" decision is the Supervisor's to make and record as an ADR in `docs/adr/`.

## Problem

Founders starting a US company have to work through many separate steps: choose the
entity type and state, understand the legal implications, find a name that's free
(including the domain), draft founding documents, split equity, register the company,
buy the domain and put up a website. Each step usually means a different person or tool.

## What the product does

A founder talks to one **Manager Agent** in a chat. The Manager works out what the founder
wants and brings in specialist agents as needed. Each specialist can talk to the founder
directly in the same conversation, and the founder always sees which agent is speaking.
By the end the founder has a chosen and verified name, a domain to buy, signed founding
documents, a cap table, a live website that passed QA, and a step-by-step registration guide.

```
Founder <──chat──> Manager Agent ──routes questions / hands over──┬─> Law Agent
                                                                   ├─> Name Agent
                                                                   ├─> Website Agent <──> QA Agent
                                                                   ├─> Registration Guide Agent
                                                                   └─> Cap Table Builder, Sign-off (deterministic)
```

## Agents and capabilities

1. **Manager Agent (LLM, the only entry point).**
   - Talks with the founder to understand the business and gathers the case facts:
     business description, founders (name, email, equity %, vesting months, cliff months),
     entity type (`LLC` or `Delaware C-Corp`), state of formation, incorporation date,
     name preferences, and what the website should contain.
   - Decides which specialist the founder needs and hands the conversation over to it
     (e.g. a legal question goes to the Law Agent), then takes it back. Remembers the
     case across many chat turns.
   - Validation is deterministic code, not the LLM: equity must total exactly 100%; each
     cliff no longer than its vesting; 83(b) deadline = incorporation date + 30 days.
     Default vesting when not stated: 48 months with a 12-month cliff, stated to the user.
   - When facts are missing or invalid, it asks follow-up questions.
2. **Law Agent (LLM).**
   - Discusses the legal side with the founder in the chat: LLC vs C-Corp, choice of
     state, liability protection, operating agreement basics, tax treatment, founder
     vesting and the 83(b) election. Raises legal issues it spots in the case (e.g.
     unequal vesting, name conflicts reported by the Name Agent).
   - Drafts the founding documents from the locked facts: Founder IP Assignment
     Agreement, Bylaws Summary (Operating Agreement summary for an LLC), and an IRS
     83(b) Election Form per founder. Unknown details stay as placeholders such as
     `[ADDRESS]`. Share counts must match the cap table exactly.
   - Every answer and document carries a "not legal advice; have a lawyer review" notice.
3. **Name Agent (LLM + live checks).**
   - Suggests company names that fit the business and the founder's preferences.
   - Checks domain availability **live** (at least `.com`, `.co`, `.io`) using free RDAP
     lookups; reports available / taken / unknown honestly.
   - States can't be checked through a free API, so it gives the state's official
     business-name search link and the USPTO trademark search link, and marks state
     availability as "check manually".
   - The founder picks a name; it becomes the company name in the case.
4. **Cap Table Builder (deterministic).** Splits 10,000,000 authorized shares (units for
   an LLC) by equity %, always summing to exactly 10,000,000. Monthly vesting schedule
   with the cliff: nothing vests before the cliff, the accrued portion vests at the cliff,
   then the rest monthly. Exports CSV and Excel.
5. **Multi-party sign-off (deterministic).** Each document has a version number. When
   every founder has signed the current version it becomes `Executed`. An edit raises the
   version and cancels the other founders' signatures (the editor's signature moves to
   the new version). Acting on a stale version is rejected. Every action goes into an
   audit log. When all documents are executed, the legal step is complete.
6. **Website Agent (LLM).**
   - Builds a static website (HTML/CSS, no build step) for the new company from what
     the founder said: name, what the business does, services, about the founders,
     contact details, and any pages the founder asked for.
   - Shows a preview in the app and lets the founder ask for changes in the chat.
   - **Deploys it live** to a hosting provider configured by environment variables
     (provider choice is an ADR decision). Without a hosting token, it still builds the
     site, shows the preview and offers a download, and says that deploy is not configured.
7. **QA Agent (LLM + deterministic checks).**
   - Checks the generated website against the founder's stated requirements before
     every deploy: every requested page and piece of content is present, the company name
     and contact details are correct, internal links work, basic accessibility (alt text,
     headings, contrast-safe defaults) and valid HTML structure.
   - Returns pass/fail with a list of issues. On fail, the Website Agent fixes the issues
     (at most 2 automatic fix rounds), then QA runs again. The QA report is shown to the
     founder. A site that still fails is not deployed without the founder's explicit OK.
8. **Registration Guide Agent (LLM + curated data).**
   - Gives a step-by-step, state-specific guide to register the company: name
     reservation (if any), filing the Certificate of Formation / Articles of
     Organization, registered agent, filing fees and official links, EIN from the IRS,
     operating agreement, 83(b) filing before the deadline, and ongoing state
     obligations (annual report / franchise tax).
   - Guides the founder through buying the chosen domain (which registrar options,
     what to check, connecting it to the deployed website).
   - Shows the guide as a checklist the founder can tick off; progress is saved.
   - First release: full guides for Delaware and Wyoming; any other state gets a generic
     checklist plus a link to that state's filing office. Official sources are linked,
     and the guide states when its fee and rule data was last reviewed.

## Platform

- **Backend:** FastAPI with a SQLite database.
- **UI:** Streamlit, with: a chat that labels which agent is speaking; a founder switcher;
  an 83(b) deadline countdown; Names & Domains; Legal documents with review and sign-off;
  Cap Table with downloads; Website (preview, QA report, deploy status and live URL);
  Registration Guide checklist; Audit trail.
- **LLM provider:** OpenAI-compatible providers (DeepSeek primary, Groq for now), chosen
  by configuration with no code change.
- **External services** (RDAP, hosting provider) sit behind interfaces with fakes, so tests
  and recorded runs need no network and no paid keys. Live calls are only used when
  configured.

## Scope limits

- US only: `LLC` or `Delaware C-Corp`. Full registration guides for Delaware and Wyoming only.
- The app guides and drafts; it does not file with the state or buy the domain itself.
- Generated documents and guidance are not legal advice.
- No real authentication or e-signature in the first release (state it as a limitation).

## Definition of done for the product

- The founder can go from a first chat message to: a verified name and domain choice,
  executed founding documents, a cap table, a QA-passed live (or packaged) website, and a
  registration checklist, all through the API and the UI.
- An automated test suite covers the deterministic rules, the agent routing, the QA
  loop and the API flows (LLM, RDAP and hosting faked).
- Each merged change has a recorded feature run.
- Each significant design decision has an ADR.
