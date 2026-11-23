# ADR-0032: Application services and the HTTP API v2 (authenticated)

| | |
|---|---|
| **Status** | Accepted; billing routes changed by [ADR-0038](0038-plans-v2-free-launch-team-and-plan-settings.md) |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (views, ports, app skeleton), T-013/T-014/T-015 (services), T-016 (composition, app, deps), T-017/T-039/T-040/T-041 (routes), T-011 + waves 4–6 (client) |
| **Scope** | `domain/views.py`, `workflows/`, `composition.py`, `api/` |

## Context

ADR-0017 defined three services and the endpoint list for an app without accounts
(`founder_id` in request bodies). Every endpoint must now be authorized, the actor comes
from the session, long work returns a job, and accounts, team, billing, privacy and
admin need endpoints. This ADR **supersedes ADR-0017**. Unchanged from ADR-0017: the
view types and progress rules (with the additions below), the error envelope, thin
routers, the SPA mount, the sandboxed website preview, request/response chat with a
typing indicator.

## Decision

### Views (`domain/views.py`, T-001; additions to ADR-0017's)

```python
class CaseView(...ADR-0017 fields...):          # added fields
    my_role: MemberRole | None; my_founder_id: str | None
    plan: PlanId                                # the company's entitlements
    active_jobs: list[JobRecord]
class PostMessageResult(...ADR-0017 fields...): jobs: list[JobRecord] = []
class SiteJobOutcome(BaseModel): job: JobRecord; build: SiteBuild | None
class MeView(BaseModel):
    user: User; plan: PlanId; subscription: Subscription; email_verified: bool
    companies: list[CaseSummary]; csrf_token: str
class MemberView(BaseModel):
    user_id: str; full_name: str; email: str; role: MemberRole
    founder_id: str | None; founder_name: str | None; joined_at: datetime
class InvitePreview(BaseModel):
    company_name: str | None; inviter_name: str; email_hint: str   # "a***@example.com"
    founder_name: str | None; expired: bool
class PublicConfig(BaseModel):
    brand_name: str; demo_mode: bool; payments_test_mode: bool
    hosting_configured: bool; plans: list[Plan]; esign_consent_text: str; esign_consent_version: str
```

### Services (protocols in `workflows/ports.py`, T-001)

```python
class LegalServicePort(Protocol):                      # workflows/legal.py (T-015)
    def cap_table(self, access: CaseAccess) -> CapTable
    def cap_table_csv(self, access: CaseAccess) -> str
    def cap_table_xlsx(self, access: CaseAccess) -> bytes
    def generate_documents(self, access: CaseAccess) -> DocumentsOutcome     # DOCUMENTS; FactsNotReadyError unless locked
    def regenerate_if_drafted(self, access: CaseAccess) -> DocumentsOutcome  # called by CaseService after re-lock
    def list_documents(self, access: CaseAccess) -> list[Document]
    def get_document(self, access: CaseAccess, document_id: str) -> Document  # NotFoundError if not in this company
    def sign(self, access: CaseAccess, document_id: str, req: SignRequest) -> Document
    def edit(self, access: CaseAccess, document_id: str, req: EditRequest) -> EditOutcome
    def signed_pdf(self, access: CaseAccess, document_id: str) -> tuple[str, bytes]   # (filename, bytes)
    def docx(self, access: CaseAccess, document_id: str) -> tuple[str, bytes]
    def audit(self, access: CaseAccess) -> list[AuditEntry]
    def legal_complete(self, access: CaseAccess) -> bool

class WebsiteServicePort(Protocol):                    # workflows/website.py (T-013)
    def request_build(self, access: CaseAccess, change_request: str | None = None) -> JobRecord  # NameNotChosenError
    def request_deploy(self, access: CaseAccess, *, override_qa: bool = False) -> JobRecord     # WEBSITE_DEPLOY
    def run_build(self, case_id: str, change_request: str | None, actor: Actor) -> SiteBuildOutcome  # job handler
    def run_deploy(self, case_id: str, actor: Actor, *, override_qa: bool) -> SiteBuildOutcome      # job handler
    def latest(self, access: CaseAccess) -> SiteBuild | None
    def preview_file(self, access: CaseAccess, path: str) -> SiteFile
    def download_zip(self, access: CaseAccess) -> bytes

class SignRequest(BaseModel):  version: int; content_sha256: str; typed_name: str; consent: Literal[True]
class EditRequest(SignRequest): content: str
```

```python
class CaseService:                                     # workflows/case.py (T-014)
    def __init__(self, repo: Repository, team: TeamService, *, turn_handler: TurnHandler,
                 agent_deps: Callable[[CaseAccess], AgentDeps],   # wraps the LLM with metering (ADR-0033)
                 legal: LegalServicePort, website: WebsiteServicePort, jobs: JobRunner,
                 entitlements: EntitlementsProvider, scrubber: Callable[[str], ScrubResult],
                 clock=utcnow, today: Callable[[], date] | None = None)
    def create_case(self, ctx: RequestContext) -> CaseView        # creator = OWNER + billing user; max_companies
    def list_cases(self, ctx: RequestContext) -> list[CaseSummary]   # member companies only
    def get_view(self, access: CaseAccess) -> CaseView
    def list_messages(self, access: CaseAccess, after_seq: int | None = None) -> list[ChatMessage]
    def post_message(self, access: CaseAccess, text: str) -> PostMessageResult
    def choose_name(self, access: CaseAccess, name: str, domain: str | None = None) -> CaseView
    def recheck_names(self, access: CaseAccess) -> list[NameCandidate]
    def get_guide(self, access: CaseAccess) -> GuideView
    def set_guide_item(self, access: CaseAccess, item_id: str, done: bool) -> GuideView
    def delete_case(self, access: CaseAccess) -> None               # DELETE_COMPANY
```

`post_message` is as in ADR-0017 plus: the founder text passes the PII scrubber first
(ADR-0033); the stored founder message carries `founder_id = access.founder_id`;
`BuildWebsite` / `DeployWebsite` actions enqueue jobs (returned in `jobs`) and the
Website Agent's reply says the build has started; when `LockFacts` links the owner's
membership to the matching founder (by email) if not linked yet.

### Composition (`composition.py`, T-016)

```python
@dataclass
class Services:
    settings: Settings; engine: Engine; repo: Repository
    accounts: AccountsRepository; team_repo: TeamRepository
    auth: AuthService; team: TeamService; billing: BillingService; entitlements: EntitlementsProvider
    case: CaseService; legal: LegalServicePort; website: WebsiteServicePort
    jobs: JobRunner; job_registry: JobRegistry; mailer: Mailer; notifier: Notifier
    privacy: PrivacyService; admin: AdminService; limiter: RateLimiter
    llm: LLMProvider; domain_checker: DomainChecker; host: SiteHost; payments: PaymentGateway
def build_services(settings: Settings, *, jobs: JobRunner | None = None) -> Services
```

### HTTP API (prefix `/api`; JSON; cookie session; CSRF header on unsafe methods, ADR-0033)

Auth column: **public**, **user** (logged in), **case:P** (member with permission P via
`require_case(P)`), **admin**. Rate-limit classes from ADR-0033 in brackets.

| Method + path | Body | Returns | Auth | Ticket |
|---|---|---|---|---|
| GET `/api/health` | — | `{status: "ok"}` | public | T-016 |
| GET `/api/ready` | — | `{status, checks}` (503 when not ready) | public | T-016 |
| GET `/api/config` | — | `PublicConfig` | public | T-016 |
| GET `/api/agents` | — | `list[AgentProfile]` | public | T-016 |
| POST `/api/auth/signup` | `{email, password, full_name, accept_terms: true}` | `MeView` 201 [auth] | public | T-039 |
| POST `/api/auth/login` | `{email, password}` | `MeView` [auth] | public | T-039 |
| POST `/api/auth/logout` | — | 204 | user | T-039 |
| GET `/api/auth/me` | — | `MeView` (401 when logged out) | public | T-039 |
| POST `/api/auth/verify-email` | `{token}` | `MeView` | public | T-039 |
| POST `/api/auth/resend-verification` | — | 204 [email] | user | T-039 |
| POST `/api/auth/forgot-password` | `{email}` | 204 always [email] | public | T-039 |
| POST `/api/auth/reset-password` | `{token, password}` | 204 [auth] | public | T-039 |
| PATCH `/api/account` | `{full_name}` | `MeView` | user | T-039 |
| POST `/api/account/password` | `{current_password, new_password}` | 204 [auth] | user | T-039 |
| GET `/api/account/export` | — | zip download | user | T-039 |
| DELETE `/api/account` | `{password, confirm: "DELETE"}` | 204 | user | T-039 |
| GET `/api/cases/{id}/members` | — | `list[MemberView]` | case:VIEW | T-039 |
| GET / POST `/api/cases/{id}/invites` | POST `{email, founder_id?}` | `list[Invite]` / `Invite` 201 [invite] | case:MANAGE_TEAM | T-039 |
| DELETE `/api/cases/{id}/invites/{invite_id}` | — | 204 | case:MANAGE_TEAM | T-039 |
| DELETE `/api/cases/{id}/members/{user_id}` | — | 204 | case:VIEW (self) / MANAGE_TEAM | T-039 |
| GET `/api/invites/{token}` | — | `InvitePreview` | public | T-039 |
| POST `/api/invites/{token}/accept` | — | `{case_id}` | user | T-039 |
| POST / GET `/api/cases` | — | `CaseView` 201 / `list[CaseSummary]` | user | T-041 |
| GET / DELETE `/api/cases/{id}` | — | `CaseView` / 204 | case:VIEW / DELETE_COMPANY | T-041 |
| GET `/api/cases/{id}/messages?after_seq=` | — | `list[ChatMessage]` | case:VIEW | T-041 |
| POST `/api/cases/{id}/messages` | `{text}` (<= 4,000 chars) | `PostMessageResult` [llm] | case:CHAT | T-041 |
| GET `/api/cases/{id}/names` | — | `list[NameCandidate]` | case:VIEW | T-041 |
| POST `/api/cases/{id}/names/choose` | `{name, domain?}` | `CaseView` | case:CHAT | T-041 |
| POST `/api/cases/{id}/names/recheck` | — | `list[NameCandidate]` [llm] | case:CHAT | T-041 |
| GET `/api/cases/{id}/guide` | — | `GuideView` | case:VIEW | T-041 |
| PUT `/api/cases/{id}/guide/items/{item_id}` | `{done}` | `GuideView` | case:TICK_GUIDE | T-041 |
| GET `/api/cases/{id}/jobs` / `/api/cases/{id}/jobs/{job_id}` | — | `list[JobRecord]` / `JobRecord` | case:VIEW | T-041 |
| GET `/api/cases/{id}/cap-table` (+ `.csv`, `.xlsx`) | — | `CapTable` / file | case:VIEW | T-017 |
| GET `/api/cases/{id}/documents` | — | `list[Document]` | case:VIEW | T-017 |
| POST `/api/cases/{id}/documents/generate` | — | `DocumentsOutcome` | case:EDIT_DOCUMENTS | T-017 |
| GET `/api/cases/{id}/documents/{doc_id}` | — | `Document` | case:VIEW | T-017 |
| POST `/api/cases/{id}/documents/{doc_id}/sign` | `SignRequest` | `Document` | case:SIGN | T-017 |
| POST `/api/cases/{id}/documents/{doc_id}/edit` | `EditRequest` | `EditOutcome` | case:EDIT_DOCUMENTS | T-017 |
| GET `/api/cases/{id}/documents/{doc_id}/pdf` / `/docx` | — | file | case:VIEW | T-017 |
| GET `/api/cases/{id}/audit` | — | `list[AuditEntry]` | case:VIEW | T-017 |
| GET `/api/cases/{id}/website` | — | `SiteBuild \| null` | case:VIEW | T-017 |
| POST `/api/cases/{id}/website/build` | `{change_request?}` | `SiteJobOutcome` 202 [llm] | case:BUILD_WEBSITE | T-017 |
| POST `/api/cases/{id}/website/deploy` | `{override_qa}` | `SiteJobOutcome` 202 | case:DEPLOY | T-017 |
| GET `/api/cases/{id}/website/preview/{path}` / `download` | — | file / zip | case:VIEW | T-017 |
| GET `/api/billing/plans` | — | `list[Plan]` | public | T-040 |
| GET `/api/billing/subscription` | — | `Subscription` | user | T-040 |
| POST `/api/billing/checkout` | `{plan, interval}` | `{url}` | user | T-040 |
| POST `/api/billing/portal` | — | `{url}` | user | T-040 |
| POST `/api/billing/webhook` | Stripe event | 200 (no CSRF, signature checked) | public | T-040 |
| POST `/api/billing/test-checkout/{session_id}/complete` | — | 204 (fake gateway only) | user | T-040 |
| GET `/api/admin/users`, `/cases`, `/usage`, `/jobs?status=`, `/emails?status=`, `/system` | — | read models (ADR-0034) | admin | T-040 |
| POST `/api/admin/jobs/{job_id}/retry` | — | `JobRecord` | admin | T-040 |

Routes stay thin: parse, call `require_case`/`require_user`/`require_admin`, call one
service method, return the view. Files use `Content-Disposition: attachment` with a
safe file name. Unknown company ids and other customers' companies both return 404.

### App (`api/app.py`, T-016)

`create_app(services: Services | None = None, settings: Settings | None = None) -> FastAPI`
installs, in order: request-id + structured logging middleware (ADR-0034), security
headers, CORS (`settings.cors_origins`, credentials allowed), CSRF check, the 100 s
request timeout for chat (ADR-0023), the error envelope handlers (ADR-0017 rules plus
the new error codes), the routers `api/routes/{cases,jobs,legal,website,auth,account,team,billing,admin}.py`
(each `router = APIRouter()`, stubbed by T-001), and the SPA mount (fallback to
`index.html` for non-`/api` paths). It starts the embedded job worker and the scheduler
when `jobs_embedded_worker` is on, and stops them on shutdown. `api/deps.py` provides
`get_services`, `get_ctx` (builds `RequestContext` from the session cookie, IP per
`TRUSTED_PROXY_COUNT`, user agent, demo-mode header), `require_user`, `require_admin`,
`require_case(permission)` and `rate_limit(class)`.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. `CaseAccess` passed into services, auth in one dependency, jobs for long work (chosen) | Every endpoint authorized the same way; services testable without HTTP | Every service signature changed once, now |
| B. Auth checks inside each route | Explicit | Easy to forget one; duplicated |
| C. Separate public API with API keys | Integrations | Not needed for v1 |

## Consequences

- The frontend's `types.ts` mirrors these views; T-016 tests compare OpenAPI field
  names with this ADR, and a test walks every registered route to assert it declares an
  auth dependency (public routes are an explicit allow-list).
- Document routes now live under the company path, so authorization is uniform.
