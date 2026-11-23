# ADR-0038: Plans v2: Free, Launch and Team, with amounts as settings

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor, product owner (Q-006: three tiers; support reply times: open question Q-009) |
| **Tickets** | T-001 (types, settings, ports, fakes), T-029 (billing), T-032 (allowance message), T-014 (company limit), T-038 / T-045 (admin), T-040 (routes), T-016 (wiring), T-011 (`PlanGate`, support link), T-043 (pricing page), T-044 (billing settings), T-034 (Stripe setup guide), T-023 (journey) |
| **Scope** | `domain/billing.py`, `config.py` (billing settings), `ports/payments.py`, `ports/entitlements.py`, `billing/`, `/api/billing/*`, the pricing and billing screens |

## Context

The product owner answered Q-006 with **three tiers: Free, Launch at $29 a month and
Team at $79 a month** (Team: more companies and AI messages, priority support), not the
two-plan default in ADR-0030. They also asked that amounts stay settings. This ADR
**supersedes the "Default pricing" section and the `PlanId` / `Plan` / `Entitlements`
contracts of ADR-0030**, extends the billing settings of ADR-0021, the billing routes of
ADR-0032 and the admin queries of ADR-0034. Everything else in ADR-0030 (Stripe Checkout
and portal, webhooks processed once, entitlement from the billing user, gates, test mode,
nothing deleted on downgrade) still holds.

## Decision

### What each plan includes (defaults; every number is a setting)

| | **Free** | **Launch** | **Team** |
|---|---|---|---|
| Price | $0 | **$29 / month** or $290 / year | **$79 / month** or $790 / year |
| Companies you can create | 1 | 3 | 15 |
| AI messages per month | 300 | 2,000 | 10,000 |
| Chat with every agent, legal Q&A, name ideas with live domain checks, cap table with CSV/Excel, website preview and .zip download, registration checklist, 83(b) reminders | yes | yes | yes |
| Founding documents drafted, electronic signatures, signed PDF and Word downloads | no | yes | yes |
| Website publishing | no | yes | yes |
| Co-founders invited to your companies | free, unlimited | free, unlimited | free, unlimited |
| Support | Help guides and email, best effort | Email, reply within 2 business days | Priority email, reply within 1 business day, answered first |

- **Yearly prices exist** and are "two months free" (10 x the monthly price). One setting,
  `BILLING_YEARLY_ENABLED` (default on), hides the yearly option everywhere.
- **"AI message"** on the pricing page means one request to the AI model by any agent
  (the unit ADR-0033 already meters). A footnote says: "Each agent reply or work step
  uses one AI message; building and checking a website uses several." The allowance is
  per billing user per calendar month (UTC), across all their companies.
- **Team** is pitched at serial founders, studios and advisers who set up several
  companies. Its features are the same as Launch; only limits and support differ. The
  name does not mean seats: co-founders are free on every plan.
- **Changing plans:** Free -> paid goes through Stripe Checkout. Launch <-> Team (and
  monthly <-> yearly) is an in-app "Switch plan" that updates the existing Stripe
  subscription with proration (no second subscription). Paid -> Free is cancellation in
  the Stripe portal; the plan lasts until the period ends.
- **Over a limit after a downgrade:** existing companies stay fully usable and nothing is
  deleted; only creating another company is blocked until the user is under the limit.
- **Support level** is delivered by the owner over email (`SUPPORT_EMAIL`). The app's help
  menu has "Contact support", a `mailto:` whose subject starts with `[{Plan name}]` and the
  request id of the last error, so Team mail is easy to spot; the admin users list can be
  filtered by plan. The reply times above are the default promise pending Q-009.

### Contracts (T-001; replace the ADR-0030 versions)

```python
class PlanId(str, Enum): FREE = "free"; LAUNCH = "launch"; TEAM = "team"
class SupportLevel(str, Enum): BASIC = "basic"; STANDARD = "standard"; PRIORITY = "priority"
class PlanAmounts(BaseModel):
    price_month_cents: int; price_year_cents: int; max_companies: int; ai_messages_per_month: int
DEFAULT_PLAN_AMOUNTS: Mapping[PlanId, PlanAmounts]       # the table above
class Plan(BaseModel):
    id: PlanId; rank: int                                # 0 free, 1 launch, 2 team
    name: str; tagline: str
    price_month_cents: int; price_year_cents: int        # 0 for free
    yearly_available: bool                               # False for free or when yearly is disabled
    features: list[Feature]; max_companies: int; llm_calls_per_month: int
    support: SupportLevel; support_label: str            # "Priority email, reply within 1 business day"
    highlights: list[str]                                # pricing-card bullets, built from the amounts
def build_plans(amounts: Mapping[PlanId, PlanAmounts] = DEFAULT_PLAN_AMOUNTS, *,
                yearly_enabled: bool = True) -> dict[PlanId, Plan]
PLANS: Mapping[PlanId, Plan] = build_plans()             # defaults, for tests and fakes
def lowest_plan_with(feature: Feature, plans: Mapping[PlanId, Plan] = PLANS) -> Plan
def next_plan_for_companies(current: PlanId, plans: Mapping[PlanId, Plan] = PLANS) -> Plan | None
class Entitlements(BaseModel):
    plan: PlanId; features: frozenset[Feature]; max_companies: int; llm_calls_per_month: int
    support: SupportLevel
    def has(self, feature: Feature) -> bool: ...
    @classmethod
    def for_plan(cls, plan: PlanId, plans: Mapping[PlanId, Plan] = PLANS) -> "Entitlements": ...
class UsageCounter(Protocol):                            # ports/entitlements.py
    def ai_messages_this_month(self, user_id: str) -> int: ...
    def companies_created(self, user_id: str) -> int: ...
class UsageSummary(BaseModel):
    ai_messages_used: int; ai_messages_limit: int; resets_on: date
    companies_used: int; companies_limit: int
class BillingOverview(BaseModel):                        # domain/views.py
    subscription: Subscription; plan: Plan; usage: UsageSummary
    can_switch_plan: bool                                # an active paid subscription exists
class PriceCheck(BaseModel):
    plan: PlanId; interval: BillingInterval; price_id: str | None
    expected_cents: int; provider_cents: int | None; ok: bool; problem: str | None
```

`Feature`, `BillingInterval`, `SubscriptionStatus`, `Subscription`, `CheckoutSession`
and `PaymentEvent` are unchanged. `CaseAccess.require_feature` puts
`details={"feature": ..., "required_plan": lowest_plan_with(feature).id}` on
`PlanRequiredError`; the company limit sets `required_plan` to
`next_plan_for_companies(...)` and the message "Your plan includes {n} companies.
Upgrade to {plan} to add more." (on Team: "Contact support to add more.").

`PaymentGateway` gains two methods (the fake implements both):

```python
    def change_subscription_price(self, *, subscription_id: str, price_id: str) -> PaymentEvent: ...
        # Stripe: Subscription.modify with the item's new price, proration_behavior="create_prorations"
        # Fake: returns the customer.subscription.updated event it would send (also delivered via parse_webhook)
    def price_amount(self, price_id: str) -> tuple[int, BillingInterval] | None: ...   # None if unknown
```

### Settings (additions to ADR-0021, implemented in T-001)

| Setting | Env | Default |
|---|---|---|
| `stripe_price_team_monthly`, `stripe_price_team_yearly` | `STRIPE_PRICE_TEAM_MONTHLY`, `STRIPE_PRICE_TEAM_YEARLY` | none |
| `billing_yearly_enabled` | `BILLING_YEARLY_ENABLED` | `true` |
| `plan_amounts: dict[PlanId, PlanAmounts]` | `PLAN_{FREE,LAUNCH,TEAM}_{PRICE_MONTH_CENTS,PRICE_YEAR_CENTS,MAX_COMPANIES,AI_MESSAGES}` (each optional, overrides one number) | `DEFAULT_PLAN_AMOUNTS` |
| `support_email` | `SUPPORT_EMAIL` | none (help menu then shows the help link only) |

`Settings.plans() -> dict[PlanId, Plan]` returns `build_plans(plan_amounts,
yearly_enabled=billing_yearly_enabled)`; it is the only source of plans for services,
`/api/billing/plans` and `PublicConfig.plans`. Production guards add: with Stripe, all
four monthly/yearly price ids must be set (yearly ones only when yearly is enabled); a
paid plan priced at 0, a negative number, or a Free price above 0 is a `ConfigError`;
`SUPPORT_EMAIL` must be set. `PublicConfig` gains `support_email: str | None` and
`yearly_enabled: bool`.

### Billing service (T-029; additions and changes to ADR-0030)

```python
class BillingService:
    def __init__(self, billing: BillingRepository, accounts: AccountsRepository,
                 gateway: PaymentGateway, settings: Settings, *,
                 usage: UsageCounter | None = None, clock=utcnow) -> None
    def plans(self) -> list[Plan]                                        # settings.plans(), by rank
    def overview(self, user: User) -> BillingOverview                    # usage zeros when usage is None
    def start_checkout(self, user: User, plan: PlanId, interval: BillingInterval) -> CheckoutSession
        # FREE, unknown plan, or yearly while disabled -> InvalidStateError;
        # an active paid subscription -> ConflictError("You already have a plan. Use Switch plan.")
    def change_plan(self, user: User, plan: PlanId, interval: BillingInterval) -> Subscription
        # needs an active paid subscription (else ConflictError); FREE -> InvalidStateError
        # ("Cancel in Manage billing to return to Free."); same plan+interval -> unchanged
    def check_prices(self) -> list[PriceCheck]                           # each paid plan x interval vs the gateway
def price_id_for(settings: Settings, plan: PlanId, interval: BillingInterval) -> str
def plan_for_price(settings: Settings, price_id: str) -> tuple[PlanId, BillingInterval] | None
```

Webhooks set the subscription's plan and interval from the event's `price_id` through
`plan_for_price`; an unknown price id is recorded, logged as a warning and leaves the
plan unchanged. `DbEntitlements(billing, plans)` uses `Settings.plans()`. The composition
root (T-016) wires a `UsageCounter` over the `llm_usage` table and the companies table.

### API (changes to ADR-0032, T-040)

| Method and path | Body | Returns | Access |
|---|---|---|---|
| GET `/api/billing/subscription` | — | `BillingOverview` (was `Subscription`) | user |
| POST `/api/billing/change-plan` | `{plan, interval}` | `Subscription` | user, CSRF |
| GET `/api/admin/users?plan=` | — | as ADR-0034, optional plan filter | admin |
| GET `/api/admin/system` | — | `SystemInfo` plus `price_checks: list[PriceCheck]` | admin |

### Allowance message (ADR-0033 wording, T-032)

`UsageLimitError` names the plan and the reset date and the next step: Free and Launch
"Upgrade to {next plan} or wait until {date}."; Team "Your allowance resets on {date}.
Contact support if you need more before then."

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Three tiers as data built from settings, plan switch through the existing subscription (chosen) | Owner's choice; any number changes with one env value; no double billing | Two more Stripe prices to set up; displayed and charged amounts must match (checked) |
| B. Keep amounts only in code (`PLANS` table) | Simpler | Every price change is a code change; owner asked for settings |
| C. Plan switch through a second Checkout | No new gateway method | Customers could end up with two subscriptions |
| D. No yearly prices | Simpler pricing page | Loses the usual discount for committed customers; one setting turns it off anyway |

## Consequences

- The owner creates four Stripe prices (Launch and Team, monthly and yearly), enables the
  customer portal's cancellation and invoices, and sets `SUPPORT_EMAIL`. The admin system
  page flags any price whose Stripe amount or interval differs from the setting
  (`AdminService` receives `BillingService.check_prices` as a callable, T-038).
- Changing a price = a new Stripe price + two env values (price id and amount); no code.
- AI allowances are a cost decision: at the default model a heavy Team account can cost
  real money each month, so the operations guide tells the owner to watch the admin
  usage page and lower `PLAN_*_AI_MESSAGES` or use cheaper per-agent models if needed.
