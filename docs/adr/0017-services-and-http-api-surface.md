# ADR-0017: Application services and the HTTP API surface

| | |
|---|---|
| **Status** | Superseded by ADR-0032 |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (views, ports, app skeleton), T-013/T-014/T-015 (services), T-016/T-017 (API), T-011 + wave 4 (client) |
| **Scope** | `launch_agents/domain/views.py`, `launch_agents/workflows/`, `launch_agents/composition.py`, `launch_agents/api/` |

## Context

The UI and the end-to-end tests need one typed API covering the whole brief. Routes must
stay thin, so the behaviour lives in three application services built in parallel in
wave 2. Their signatures, the response views and the endpoint list are fixed here.

## Decision

### Views (`domain/views.py`)

```python
class StepId(str, Enum): FACTS="facts"; NAME="name"; LEGAL="legal"; CAP_TABLE="cap_table"; WEBSITE="website"; REGISTRATION="registration"
class StepStatus(str, Enum): NOT_STARTED="not_started"; IN_PROGRESS="in_progress"; DONE="done"; ATTENTION="attention"
class StepProgress(BaseModel): id: StepId; label: str; status: StepStatus; detail: str
class Progress(BaseModel): steps: list[StepProgress]; percent: int          # done steps * 100 // 6
class CaseView(BaseModel):
    id: str; created_at: datetime; updated_at: datetime
    facts: CaseFacts; facts_locked: bool; active_agent: AgentId
    company_name: str | None; chosen_domain: str | None
    validation_issues: list[ValidationIssue]; missing_facts: list[str]
    deadline_83b: date | None; days_until_83b: int | None
    progress: Progress; legal_issues: list[LegalIssue]
class CaseSummary(BaseModel): id: str; company_name: str | None; created_at: datetime; updated_at: datetime; percent: int
class GuideView(BaseModel): guide: RegistrationGuide; done: dict[str, bool]; done_count: int; total: int
class PostMessageResult(BaseModel):
    messages: list[ChatMessage]            # the founder's message first, then every new message
    case: CaseView; open_view: str | None  # last OpenView action, a UI hint
class DocumentsOutcome(BaseModel): documents: list[Document]; messages: list[ChatMessage]
class EditOutcome(BaseModel): document: Document; invalidated: list[str]
class SiteBuildOutcome(BaseModel): build: SiteBuild; messages: list[ChatMessage]
```

Progress rules (computed in `CaseService.get_view`): facts = done when locked, attention
when validation issues; name = done when `company_name` set, in_progress when candidates
exist; legal = done when all documents executed, in_progress when any exist; cap_table =
done when facts validate; website = done when deployed **or** QA passed with deploy not
configured ("packaged"), attention when QA failed, in_progress when a build exists;
registration = done when every non-optional step is ticked, in_progress when any is.
`days_until_83b` < 8 or negative makes the legal step `attention` unless all 83(b)
documents are executed.

### Services (`workflows/ports.py` holds these as Protocols; T-001)

```python
class LegalServicePort(Protocol):                      # implemented by workflows/legal.py LegalService (T-015)
    def cap_table(self, case_id: str) -> CapTable
    def cap_table_csv(self, case_id: str) -> str
    def cap_table_xlsx(self, case_id: str) -> bytes
    def generate_documents(self, case_id: str, *, actor: str = "system") -> DocumentsOutcome  # FactsNotReadyError unless locked
    def list_documents(self, case_id: str) -> list[Document]
    def sign(self, document_id: str, founder_id: str, version: int) -> Document
    def edit(self, document_id: str, founder_id: str, version: int, content: str) -> EditOutcome
    def audit(self, case_id: str) -> list[AuditEntry]
    def legal_complete(self, case_id: str) -> bool

class WebsiteServicePort(Protocol):                    # workflows/website.py WebsiteService (T-013)
    def build(self, case_id: str, change_request: str | None = None) -> SiteBuildOutcome   # NameNotChosenError
    def deploy(self, case_id: str, founder_id: str | None, *, override_qa: bool = False) -> SiteBuildOutcome
    def latest(self, case_id: str) -> SiteBuild | None
    def preview_file(self, case_id: str, path: str) -> SiteFile                          # NotFoundError
    def download_zip(self, case_id: str) -> bytes
```

Constructors: `LegalService(repo, llm, *, clock=utcnow)`,
`WebsiteService(repo, llm, host: SiteHost, *, clock=utcnow)`, and

```python
class CaseService:                                     # workflows/case.py (T-014)
    def __init__(self, repo: Repository, *, turn_handler: TurnHandler, agent_deps: AgentDeps,
                 legal: LegalServicePort, website: WebsiteServicePort,
                 clock: Callable[[], datetime] = utcnow, today: Callable[[], date] | None = None)
    def create_case(self) -> CaseView                  # stores the Manager's greeting message
    def list_cases(self) -> list[CaseSummary]
    def get_view(self, case_id: str) -> CaseView
    def list_messages(self, case_id: str, after_seq: int | None = None) -> list[ChatMessage]
    def post_message(self, case_id: str, text: str, founder_id: str | None = None) -> PostMessageResult
    def choose_name(self, case_id: str, name: str, founder_id: str | None = None, domain: str | None = None) -> CaseView
    def recheck_names(self, case_id: str) -> list[NameCandidate]
    def get_guide(self, case_id: str) -> GuideView
    def set_guide_item(self, case_id: str, item_id: str, done: bool, founder_id: str | None) -> GuideView
```

`post_message`: store the founder message -> `turn_handler(TurnInput, agent_deps)` ->
save facts/state -> store agent messages -> execute actions in order (`LockFacts`: lock,
audit `FACTS_LOCKED`, regenerate documents if any exist; `ChooseName`: as `choose_name`;
`DraftDocuments`: `legal.generate_documents`; `BuildWebsite`: `website.build`;
`DeployWebsite`: `website.deploy`; `OpenView`: hint only). An action that raises a
`LaunchError` becomes a friendly message from the agent that asked for it, never a 500.

### Composition (`composition.py`, T-016)

```python
@dataclass
class Services:
    settings: Settings; repo: Repository; case: CaseService; legal: LegalServicePort
    website: WebsiteServicePort; llm: LLMProvider; domain_checker: DomainChecker; host: SiteHost
def build_services(settings: Settings) -> Services
```

### HTTP API (`api/`, prefix `/api`, JSON bodies, pydantic views above as responses)

| Method + path | Body | Returns | Ticket |
|---|---|---|---|
| GET `/api/health` | — | `{status, llm_provider, domain_checker, hosting: {provider, configured}}` | T-016 |
| GET `/api/agents` | — | `list[AgentProfile]` | T-016 |
| POST `/api/cases` | — | `CaseView` (201) | T-016 |
| GET `/api/cases` | — | `list[CaseSummary]` | T-016 |
| GET `/api/cases/{case_id}` | — | `CaseView` | T-016 |
| GET `/api/cases/{case_id}/messages?after_seq=` | — | `list[ChatMessage]` | T-016 |
| POST `/api/cases/{case_id}/messages` | `{text, founder_id?}` | `PostMessageResult` | T-016 |
| GET `/api/cases/{case_id}/names` | — | `list[NameCandidate]` | T-016 |
| POST `/api/cases/{case_id}/names/choose` | `{name, domain?, founder_id?}` | `CaseView` | T-016 |
| POST `/api/cases/{case_id}/names/recheck` | — | `list[NameCandidate]` | T-016 |
| GET `/api/cases/{case_id}/guide` | — | `GuideView` | T-016 |
| PUT `/api/cases/{case_id}/guide/items/{item_id}` | `{done, founder_id?}` | `GuideView` | T-016 |
| GET `/api/cases/{case_id}/cap-table` | — | `CapTable` (409 `facts_not_ready`) | T-017 |
| GET `/api/cases/{case_id}/cap-table.csv` / `.xlsx` | — | file download (`Content-Disposition: attachment`) | T-017 |
| GET `/api/cases/{case_id}/documents` | — | `list[Document]` | T-017 |
| POST `/api/cases/{case_id}/documents/generate` | `{founder_id?}` | `DocumentsOutcome` | T-017 |
| POST `/api/documents/{document_id}/sign` | `{founder_id, version}` | `Document` | T-017 |
| POST `/api/documents/{document_id}/edit` | `{founder_id, version, content}` | `EditOutcome` | T-017 |
| GET `/api/cases/{case_id}/audit` | — | `list[AuditEntry]` | T-017 |
| GET `/api/cases/{case_id}/website` | — | `SiteBuild \| null` | T-017 |
| POST `/api/cases/{case_id}/website/build` | `{change_request?}` | `SiteBuildOutcome` | T-017 |
| POST `/api/cases/{case_id}/website/deploy` | `{founder_id, override_qa}` | `SiteBuildOutcome` | T-017 |
| GET `/api/cases/{case_id}/website/preview/{path}` | — | the file (`text/html` / `text/css`) | T-017 |
| GET `/api/cases/{case_id}/website/download` | — | zip | T-017 |

**Errors.** Every `LaunchError` becomes `{"error": {"code", "message", "details"}}` with
its `http_status`; request validation errors become 422 with code `invalid_request` and a
friendly message; unexpected exceptions become 500 `internal` with "Something went wrong
on our side. Please try again." (logged, never a stack trace in the body).

**App.** `create_app(services: Services | None = None, settings: Settings | None = None) -> FastAPI`.
It stores services on `app.state.services` (built from `load_settings()` when not given),
`api/deps.py: get_services(request) -> Services` is the only dependency routes use, it
includes `api/routes/cases.py`, `api/routes/legal.py` and `api/routes/website.py` routers
(each exposes `router = APIRouter()`), adds CORS for `settings.cors_origins`, and when
`settings.frontend_dist` exists mounts it at `/` with SPA fallback to `index.html` for
non-`/api` paths. The website preview is served with
`Content-Security-Policy: sandbox; default-src 'self'` and is shown in a sandboxed iframe.

No authentication (first release): `founder_id` in the body says who is acting.
Chat is request/response (no streaming); the UI shows a typing indicator meanwhile.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Three services + thin routers, fixed views (chosen) | Parallel wave-2/3 work; routes trivial to test | More types up front |
| B. Routes call agents and the repository directly | Fewer layers | Logic spread across routes; hard to share with the demo seeder |
| C. Server-sent events for chat streaming | Live tokens | More moving parts; fake LLM returns instantly anyway |

## Consequences

- The frontend's `types.ts` mirrors these views field for field; T-016's tests compare the
  OpenAPI schema field names with this ADR.
- Adding an endpoint later is additive and needs no superseding ADR only if it changes no
  existing shape.
