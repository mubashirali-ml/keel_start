# ADR-0008: Shared domain contracts (types, constants, helpers, errors, views)

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (implements), every other ticket (consumes) |
| **Scope** | `launch_agents/domain/` |

## Context

Every ticket passes the same case facts, documents, cap tables, site builds and views
around. If each builder invented its own shapes, wave 2 would not fit together. These
types are the single source of truth; the frontend mirrors them by hand
(`frontend/src/api/types.ts`, ADR-0019) and the API serialises them as-is (ADR-0017).

## Decision

All models are pydantic v2 `BaseModel`s, JSON-serialisable with `model_dump(mode="json")`.
Dates are `date`, timestamps are timezone-aware UTC `datetime`. Money/fees are strings
(`"$110"`), never floats. Percentages are `Decimal`. Field names below are binding.

### `domain/constants.py`

```python
AUTHORIZED_SHARES = 10_000_000
DEFAULT_VESTING_MONTHS = 48
DEFAULT_CLIFF_MONTHS = 12
ELECTION_83B_DAYS = 30
MAX_QA_FIX_ROUNDS = 2
DOMAIN_TLDS = (".com", ".co", ".io")           # checked in this order
FULL_GUIDE_STATES = ("DE", "WY")
DEFAULT_SITE_PAGES = ("Home", "About", "Services", "Contact")
EQUITY_DECIMALS = 2                            # max decimal places of equity_percent
LEGAL_NOTICE = ("This is not legal advice. It was generated automatically; "
                "have a licensed attorney review it before you rely on it.")
USPTO_TRADEMARK_SEARCH_URL = "https://tmsearch.uspto.gov/search/search-information"
```

### `domain/types.py` (case facts)

```python
class EntityType(str, Enum):
    LLC = "LLC"
    C_CORP = "Delaware C-Corp"

class Founder(BaseModel):
    id: str                          # "f1", "f2", ... assigned in order of first mention, never reused
    name: str
    email: str
    equity_percent: Decimal          # 0 < x <= 100, at most EQUITY_DECIMALS places
    vesting_months: int | None = None   # None = not stated; rules apply the default
    cliff_months: int | None = None

class WebsiteRequirements(BaseModel):
    pages: list[str] = []            # page names the founder asked for; empty -> DEFAULT_SITE_PAGES
    services: list[str] = []
    about: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_address: str | None = None
    extra_content: list[str] = []    # "must include" items; QA checks each one
    style_notes: str | None = None

class CaseFacts(BaseModel):
    business_description: str | None = None
    founders: list[Founder] = []
    entity_type: EntityType | None = None
    state: str | None = None         # USPS code, "DE", "WY", ...
    incorporation_date: date | None = None
    name_preferences: list[str] = []
    company_name: str | None = None
    website: WebsiteRequirements = WebsiteRequirements()

class FounderPatch(BaseModel):
    id: str | None = None
    name: str | None = None
    email: str | None = None
    equity_percent: Decimal | None = None
    vesting_months: int | None = None
    cliff_months: int | None = None

class WebsitePatch(BaseModel):        # every field optional; lists replace, scalars overwrite
    pages: list[str] | None = None; services: list[str] | None = None; about: str | None = None
    contact_email: str | None = None; contact_phone: str | None = None
    contact_address: str | None = None; extra_content: list[str] | None = None
    style_notes: str | None = None

class FactsPatch(BaseModel):
    business_description: str | None = None
    founders: list[FounderPatch] | None = None
    remove_founder_ids: list[str] = []
    entity_type: EntityType | None = None
    state: str | None = None
    incorporation_date: date | None = None
    name_preferences: list[str] | None = None
    company_name: str | None = None
    website: WebsitePatch | None = None

def apply_patch(facts: CaseFacts, patch: FactsPatch) -> CaseFacts: ...
```

`apply_patch` (implemented in T-001) is pure: `None` fields leave values unchanged; a
`FounderPatch` matches an existing founder by `id`, else by case-insensitive email, else
by case-insensitive name, otherwise appends a new founder with the next free id; a new
founder needs `name` (missing email/equity stay empty strings / `Decimal(0)` and are
reported by validation). `entity_type == C_CORP` also sets `state = "DE"`. `state` is
upper-cased.

### `domain/state.py` (agent working memory per case)

```python
class DomainStatus(str, Enum): AVAILABLE = "available"; TAKEN = "taken"; UNKNOWN = "unknown"
class DomainCheck(BaseModel):
    domain: str; status: DomainStatus; source: str        # "rdap" | "fake"
    checked_at: datetime; detail: str | None = None
class StateNameCheck(BaseModel):
    state: str; status: Literal["check_manually"] = "check_manually"
    search_url: str; office_url: str
class NameCandidate(BaseModel):
    name: str; rationale: str; domains: list[DomainCheck]
    state_check: StateNameCheck | None; trademark_search_url: str
class LegalIssue(BaseModel):
    code: str; severity: Literal["info", "warning"]; message: str
class CaseState(BaseModel):
    active_agent: AgentId = AgentId.MANAGER
    facts_locked: bool = False
    facts_locked_at: datetime | None = None
    pending_fact: str | None = None             # key the Manager last asked for
    notices_given: list[str] = []               # e.g. "default_vesting:f1", shown once
    name_candidates: list[NameCandidate] = []
    chosen_domain: str | None = None
    legal_issues: list[LegalIssue] = []
class CaseRecord(BaseModel):
    id: str; created_at: datetime; updated_at: datetime
    facts: CaseFacts; state: CaseState
```

### Other shared modules (field lists are in the owning ADR)

| Module | Types | Defined in |
|---|---|---|
| `domain/types.py` (also) | `ValidationIssue`, `ValidationResult` | ADR-0013 |
| `domain/messages.py` | `AgentId`, `AgentProfile`, `AGENT_PROFILES`, `MessageRole`, `MessageKind`, `SuggestedReply`, `ChatMessage`, `AgentAction` union | ADR-0009 |
| `domain/cap_table.py` | `CapTableRow`, `VestingEvent`, `CapTable` | ADR-0013 |
| `domain/documents.py` | `DocumentKind`, `DocumentStatus`, `Signature`, `DraftDocument`, `Document`, `AuditAction`, `AuditEntry` | ADR-0014 |
| `domain/website.py` | `SiteSection`, `SitePage`, `SiteContact`, `SiteFounder`, `SiteContent`, `SiteFile`, `SiteBundle`, `QaCheckId`, `QaIssue`, `QaCheckResult`, `QaReport`, `SiteBuildStatus`, `SiteBuild`, `DeployResult` | ADR-0015 |
| `domain/guide.py` | `GuideLink`, `GuideStep`, `RegistrationGuide` | ADR-0016 |
| `domain/states.py` | `StateInfo`, `US_STATES`, `state_info(code)` | below |
| `domain/views.py` | `StepId`, `StepStatus`, `StepProgress`, `Progress`, `CaseView`, `CaseSummary`, `GuideView`, `PostMessageResult`, `DocumentsOutcome`, `EditOutcome`, `SiteBuildOutcome` | ADR-0017 |

### `domain/states.py`

```python
class StateInfo(BaseModel):
    code: str; name: str
    filing_office_url: str      # Secretary of State business division home page
    name_search_url: str        # official business entity / name search page
US_STATES: dict[str, StateInfo]  # 50 states + DC, curated by T-001
def state_info(code: str) -> StateInfo: ...   # KeyError-free: raises InvalidStateError
```

### `domain/helpers.py` (implemented in T-001, pure)

```python
def deadline_83b(incorporation_date: date) -> date        # + ELECTION_83B_DAYS calendar days
def days_until(deadline: date, today: date) -> int        # negative once passed
def add_months(d: date, months: int) -> date              # clamps day to month end (Jan 31 + 1 = Feb 28/29)
def slugify(text: str) -> str                             # "Crumb & Co." -> "crumb-co"
def domain_label(company_name: str) -> str                # strips LLC/Inc/Corp/Co/Corporation, lowercases, keeps [a-z0-9]
def new_id(prefix: str) -> str                            # f"{prefix}_{uuid4().hex[:12]}"
def utcnow() -> datetime
```

### `domain/errors.py`

```python
class LaunchError(Exception):
    code: str = "error"; http_status: int = 400
    def __init__(self, message: str, *, details: dict | None = None): ...
class NotFoundError(LaunchError):          code = "not_found";               http_status = 404
class InvalidStateError(LaunchError):      code = "invalid_state";           http_status = 422
class FactsNotReadyError(LaunchError):     code = "facts_not_ready";         http_status = 409
class NameNotChosenError(LaunchError):     code = "name_not_chosen";         http_status = 409
class StaleVersionError(LaunchError):      code = "stale_version";           http_status = 409
class NotASignerError(LaunchError):        code = "not_a_signer";            http_status = 403
class AlreadySignedError(LaunchError):     code = "already_signed";          http_status = 409
class DeployBlockedError(LaunchError):     code = "qa_failed_needs_override"; http_status = 409
class LLMOutputError(LaunchError):         code = "llm_unavailable";         http_status = 502
class ExternalServiceError(LaunchError):   code = "external_service";        http_status = 502
```

`message` is always friendly, founder-facing English (it is shown in the UI as-is).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. pydantic models in one `domain` package, owned by T-001 (chosen) | One source of truth; free JSON + validation; FastAPI uses them directly | Changing a field needs a new ADR |
| B. Dataclasses + hand-written serialisation | No pydantic coupling | Duplicate validation; API schemas diverge |
| C. Each ticket defines its own types | No wave-0 work | Integration breaks in wave 2 |

## Consequences

- Any field change is a cross-ticket change: a builder reports `BLOCKED`, the
  Supervisor writes a superseding ADR.
- `apply_patch` and the date helpers are implemented in wave 0 so wave-1 tickets can
  use them without waiting.
