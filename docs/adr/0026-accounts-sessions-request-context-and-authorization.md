# ADR-0026: Accounts, sessions, the request context and authorization

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor, product owner |
| **Tickets** | T-001 (types, errors, stubs), T-026 (auth), T-027 (team + access policy), T-039 (routes), T-042/T-044 (screens), every service |
| **Scope** | `launch_agents/domain/accounts.py`, `launch_agents/domain/errors.py` (additions), `accounts/`, `team/`, `access/` |

## Context

The brief: founders sign up and log in with email + password (modern hashing, secure
httpOnly session cookies, password reset by email, expiring sessions); a founder invites
co-founders by email link; each person has their own account, sees only the companies
they belong to and can act only as themselves; authorization is checked on every API
endpoint; the "act as founder" switcher exists only in demo mode. Every service built
in later waves must receive the caller in one agreed shape, decided now.

## Decision

### Vocabulary

- **User** = a person with a login (an "account"). Billing belongs to a user (ADR-0030).
- **Company** = the existing *case* (`cases` table, `case_id`). The UI says "company".
- **Membership** links a user to a company with a role, and to the **founder** in the
  case facts that this user *is* (`founder_id`, e.g. `f2`). Only that user can sign as,
  or edit documents as, that founder.

### Types (`domain/accounts.py`, T-001)

```python
class User(BaseModel):
    id: str; email: str; full_name: str
    email_verified_at: datetime | None = None
    is_admin: bool = False
    created_at: datetime
    @property
    def email_verified(self) -> bool: ...
class MemberRole(str, Enum): OWNER = "owner"; MEMBER = "member"
class Membership(BaseModel):
    case_id: str; user_id: str; role: MemberRole; founder_id: str | None; joined_at: datetime
class Invite(BaseModel):
    id: str; case_id: str; email: str; founder_id: str | None; invited_by: str
    created_at: datetime; expires_at: datetime
    accepted_at: datetime | None = None; revoked_at: datetime | None = None
class Permission(str, Enum):
    VIEW = "view"; CHAT = "chat"; SIGN = "sign"; EDIT_DOCUMENTS = "edit_documents"
    BUILD_WEBSITE = "build_website"; DEPLOY = "deploy"; TICK_GUIDE = "tick_guide"
    MANAGE_TEAM = "manage_team"; DELETE_COMPANY = "delete_company"

@dataclass(frozen=True)
class RequestContext:                       # built by the API for every request (T-016)
    request_id: str
    user: User | None
    ip: str | None = None
    user_agent: str | None = None
    demo_mode: bool = False
    act_as_founder_id: str | None = None    # X-Act-As-Founder header, honoured only in demo mode
    def require_user(self) -> User: ...     # AuthRequiredError
    @classmethod
    def system(cls, request_id: str = "system") -> "RequestContext": ...

@dataclass(frozen=True)
class Actor:                                # who performs an action, for audit and signatures
    kind: Literal["user", "system"]
    user_id: str | None; founder_id: str | None
    ip: str | None; user_agent: str | None; request_id: str
    acted_by_user_id: str | None = None     # demo act-as: the logged-in user behind the actor
    @property
    def audit_actor(self) -> str: ...       # founder_id, else user_id, else "system"

@dataclass(frozen=True)
class CaseAccess:                           # proof that the caller may touch this company
    case_id: str
    actor: Actor
    membership: Membership | None           # None only for system access
    permissions: frozenset[Permission]
    entitlements: Entitlements              # of the company's billing user (ADR-0030)
    billing_user_id: str | None
    @property
    def founder_id(self) -> str | None: ...
    def require(self, permission: Permission) -> None: ...         # ForbiddenError
    def require_feature(self, feature: Feature) -> None: ...       # PlanRequiredError
    @classmethod
    def system(cls, case_id: str, entitlements: Entitlements, *, billing_user_id: str | None = None,
               request_id: str = "system") -> "CaseAccess": ...    # all permissions, actor "system"
```

### Errors (added to `domain/errors.py`, T-001)

```python
class AuthRequiredError(LaunchError):      code = "auth_required";       http_status = 401
class InvalidCredentialsError(LaunchError): code = "invalid_credentials"; http_status = 401
class ForbiddenError(LaunchError):         code = "forbidden";           http_status = 403
class EmailNotVerifiedError(LaunchError):  code = "email_not_verified";  http_status = 403
class CsrfError(LaunchError):              code = "csrf_failed";         http_status = 403
class PlanRequiredError(LaunchError):      code = "plan_required";       http_status = 402
class RateLimitedError(LaunchError):       code = "rate_limited";        http_status = 429   # details.retry_after_s
class UsageLimitError(LaunchError):        code = "usage_limit";         http_status = 429
class ConflictError(LaunchError):          code = "conflict";            http_status = 409
class TokenInvalidError(LaunchError):      code = "token_invalid";       http_status = 400
class NotExecutedError(LaunchError):       code = "not_executed";        http_status = 409
class PaymentProviderError(LaunchError):   code = "payment_provider";    http_status = 502
class WebhookSignatureError(LaunchError):  code = "webhook_invalid";     http_status = 400
```

### Authentication (`accounts/`, T-026; storage `persistence/accounts.py`)

```python
def hash_password(password: str) -> str                    # argon2id, argon2-cffi defaults
def verify_password(stored_hash: str, password: str) -> bool
def needs_rehash(stored_hash: str) -> bool
def check_password_policy(password: str, *, email: str) -> None   # InvalidStateError with a friendly reason

class AuthService:
    def __init__(self, accounts: AccountsRepository, mailer: Mailer, settings: Settings, *,
                 clock: Callable[[], datetime] = utcnow) -> None
    def signup(self, email: str, password: str, full_name: str, *, ctx: RequestContext) -> tuple[User, SessionToken]
    def login(self, email: str, password: str, *, ctx: RequestContext) -> tuple[User, SessionToken]
    def logout(self, raw_token: str) -> None
    def resolve_session(self, raw_token: str, *, touch: bool = True) -> User | None   # None if missing/expired/revoked
    def request_email_verification(self, user: User) -> None
    def verify_email(self, raw_token: str) -> User                     # TokenInvalidError
    def request_password_reset(self, email: str, *, ctx: RequestContext) -> None   # silent for unknown emails
    def reset_password(self, raw_token: str, new_password: str) -> None  # revokes every session of the user
    def change_password(self, user: User, current: str, new: str, *, keep_session: str) -> None
    def update_profile(self, user: User, *, full_name: str) -> User
class SessionToken(BaseModel): raw: str; expires_at: datetime
```

- Passwords: 10–128 characters, not equal to the email, not in a bundled list of the
  1,000 most common passwords. Stored as argon2id hashes; rehashed on login when the
  parameters change. Emails are normalised (trimmed, lower-cased) and validated.
- Session tokens: 32 random bytes (`secrets.token_urlsafe`), only the SHA-256 hash is
  stored. Idle expiry `SESSION_IDLE_DAYS` (7), absolute expiry `SESSION_MAX_DAYS` (30).
  Login rotates (a new token every login); logout revokes; password reset or change
  revokes every other session. Cookie rules are in ADR-0033.
- One-time tokens (`auth_tokens`): purpose `verify_email` (48 h) or `password_reset`
  (1 h), random 32 bytes, stored hashed, single use. Login errors never reveal whether
  the email exists; password-reset requests always answer the same way.
- Unverified users can use the app, but **signing a document requires a verified
  email** (`EmailNotVerifiedError`); the UI shows a banner with "Resend email".

### Team and invites (`team/`, T-027; storage `persistence/team.py`)

```python
class TeamService:
    def __init__(self, team: TeamRepository, accounts: AccountsRepository, repo: Repository,
                 mailer: Mailer, settings: Settings, *, clock=utcnow) -> None
    def add_owner(self, case_id: str, user: User, *, founder_id: str | None = None) -> Membership
    def members(self, access: CaseAccess) -> list[MemberView]
    def invite(self, access: CaseAccess, *, email: str, founder_id: str | None) -> Invite   # MANAGE_TEAM
    def list_invites(self, access: CaseAccess) -> list[Invite]
    def revoke_invite(self, access: CaseAccess, invite_id: str) -> None
    def preview_invite(self, raw_token: str) -> InvitePreview                      # public; TokenInvalidError
    def accept_invite(self, raw_token: str, user: User) -> Membership              # email must match the invite
    def link_founder(self, access: CaseAccess, user_id: str, founder_id: str) -> Membership  # MANAGE_TEAM
    def remove_member(self, access: CaseAccess, user_id: str) -> None              # owner, or yourself (leave)
```

- The creator of a company is its `OWNER` and its billing user. When the Manager learns
  a founder whose email matches the owner's, that membership is linked to that founder.
- Inviting: an owner invites a founder from the case facts (prefilled email) or any
  email. The invite email holds a link with a random token (stored hashed, 7 days).
  Accepting requires being logged in with the invited email (sign up first if needed);
  the membership is linked to the invite's `founder_id`. A founder can be linked to at
  most one user per company; the last owner cannot leave.

### Authorization (`access/`, T-027)

```python
ROLE_PERMISSIONS: Mapping[MemberRole, frozenset[Permission]]   # OWNER: all; MEMBER: all but MANAGE_TEAM, DELETE_COMPANY
def authorize_case(ctx: RequestContext, case_id: str, permission: Permission, *,
                   team: TeamRepository, repo: Repository,
                   entitlements: EntitlementsProvider) -> CaseAccess
```

Rules, in order: no user -> `AuthRequiredError`; the company does not exist **or the user
is not a member** -> `NotFoundError` (ids of other customers' companies never leak);
missing permission -> `ForbiddenError`. `SIGN` and `EDIT_DOCUMENTS` also need a linked
`founder_id`. The actor is the user's founder. **Demo mode** (`ctx.demo_mode` and
`settings.demo_mode`): `act_as_founder_id` switches the actor to the member linked to
that founder (`acted_by_user_id` = the logged-in user, recorded in audit and signature
evidence); outside demo mode the header is ignored and logged. Platform admins get no
access to company content through this function (ADR-0034).

Every API route that touches a company obtains its `CaseAccess` from this function (via
the `require_case(permission)` dependency, T-016) and passes it to the service; services
call `access.require(...)` again for the permission they need (defence in depth).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Server-side sessions in our DB + memberships + one `authorize_case` (chosen) | Revocable sessions; one audited path; no new service | We own password-reset and verification flows |
| B. JWT access tokens | Stateless | Hard to revoke; token handling in the browser |
| C. Hosted auth (Auth0, Clerk) | Less code | External dependency and cost; data leaves our system; not in the approved set |

## Consequences

- Services take `CaseAccess`/`RequestContext` from wave 2 on, so adding billing gates or
  audit fields never changes their signatures again.
- "Act as founder" cannot exist in production: settings refuse demo mode there (ADR-0021).
- First-release wording "no real sign-in" (ADR-0014, ADR-0019) is obsolete.
