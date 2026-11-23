# ADR-0016: Registration guide data and checklist

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (types, `US_STATES`), T-010 (guide agent + data), T-014 (progress), T-019 (UI) |
| **Scope** | `launch_agents/domain/guide.py`, `launch_agents/agents/guide/` |

## Context

The Registration Guide Agent gives a state-specific, step-by-step guide: name
reservation, formation filing, registered agent, fees and official links, EIN, operating
agreement, 83(b) before the deadline, ongoing obligations, and buying/connecting the
domain. Full guides for Delaware and Wyoming; other states get a generic checklist plus
the state's filing-office link. The guide states when its fee/rule data was last reviewed.
Progress is saved. The app never files anything itself.

## Decision

### Types (`domain/guide.py`)

```python
class GuideLink(BaseModel): label: str; url: str
class GuideStep(BaseModel):
    id: str                       # stable across rebuilds, e.g. "formation-file", "83b-mail"
    category: Literal["name", "formation", "agent", "ein", "agreement", "83b", "domain", "ongoing"]
    title: str; detail: str       # detail: short plain-language markdown
    links: list[GuideLink] = []
    fee: str | None = None        # "$110" — strings, as published by the state
    due: date | None = None       # e.g. the 83(b) deadline
    optional: bool = False
class RegistrationGuide(BaseModel):
    state: str; state_name: str; entity_type: EntityType
    full_guide: bool              # True for DE and WY
    steps: list[GuideStep]
    last_reviewed: date           # from the curated data file
    sources: list[GuideLink]
    disclaimer: str               # LEGAL_NOTICE + "The app does not file anything for you."
```

### Curated data

`agents/guide/data/states.json` (T-010) holds the full guides:

```json
{"last_reviewed": "YYYY-MM-DD",
 "states": {"DE": {"LLC": {"steps": [...GuideStep without due...]},
                   "Delaware C-Corp": {"steps": [...]},
                   "sources": [{"label": "...", "url": "https://..."}]},
            "WY": {"LLC": {...}, "sources": [...]}}}
```

Every fee and rule must have an official source link (state Division of Corporations /
Secretary of State, IRS). Wyoming has no C-Corp path in this product (C-Corp is
Delaware only), so `WY` has only `LLC`.

Other states (`full_guide=False`): a generic checklist built from code with the same
categories, using `state_info(code).filing_office_url` and `name_search_url`, and wording
that says to confirm fees on the state site.

### Builder

```python
def build_guide(facts: CaseFacts, *, chosen_domain: str | None, deployed_url: str | None) -> RegistrationGuide
class GuideAgent:   # Specialist: explains steps (task guide.explain), returns OpenView("guide")
```

Step order: name check/reservation -> formation filing -> registered agent -> EIN (IRS
online application, free) -> operating agreement / bylaws (links to the Legal view) ->
83(b): sign, mail to the IRS by `deadline_83b`, keep proof (`due` set) -> domain: pick a
registrar (at least three named options, e.g. Cloudflare Registrar, Namecheap, Porkbun),
what to check (renewal price, WHOIS privacy, transfer lock), buy `chosen_domain` (or "your
chosen domain"), connect DNS to the deployed site (`deployed_url` or "once your site is
live") -> ongoing obligations (DE: annual franchise tax/report; WY: annual report license
tax). Missing facts (no state / entity yet) -> `FactsNotReadyError`.

### Progress

Checklist ticks are stored per `(case_id, step.id)` in `checklist_items` (ADR-0012).
`CaseService.get_guide` returns `GuideView{guide, done: dict[str, bool], done_count, total}`;
ticks for step ids no longer in the guide are ignored (not deleted). Ticking is audited
(`CHECKLIST_UPDATED`).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Curated JSON for DE/WY + generated generic guide, LLM only explains (chosen) | Facts and fees are reviewable and dated; no hallucinated fees | Data must be re-reviewed periodically |
| B. LLM writes the guide | Covers every state | Invented fees and links; not trustworthy |
| C. Scrape state sites live | Always current | Fragile; slow; legal/ToS risk |

## Consequences

- The "last reviewed" date is visible in the UI; updating fees is a data-only change.
- Adding a full guide for another state = add it to `states.json` and `FULL_GUIDE_STATES`
  (a new ADR, since the constant changes).
