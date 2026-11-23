# ADR-0030: Plans, billing with Stripe, and entitlements

| | |
|---|---|
| **Status** | Accepted; plans, prices and entitlement contracts superseded by [ADR-0038](0038-plans-v2-free-launch-team-and-plan-settings.md) |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor, product owner (pricing: open question Q-006) |
| **Tickets** | T-001 (types, ports, fakes), T-029 (billing + Stripe adapter), T-040 (routes), T-043 (pricing page), T-044 (billing settings), services that gate features |
| **Scope** | `domain/billing.py`, `ports/payments.py`, `ports/entitlements.py`, `launch_agents/billing/`, `adapters/stripe_payments.py`, `persistence/billing.py` |

## Context

The brief: Stripe Checkout and the customer portal, test mode by default and live keys by
configuration; paid features gated by plan; the pricing page, receipts and cancellation
work end to end. The pricing model is the product owner's decision (open question Q-006);
the code must make the prices and gates configuration, not logic, so the answer changes
data only.

## Decision

### Default pricing (pending Q-006)

| Plan | Price | Includes |
|---|---|---|
| **Free** | $0 | 1 company; chat with every agent; legal Q&A; name ideas with live domain checks; cap table with CSV/Excel; website preview and download; registration checklist; 83(b) reminders; 300 AI messages a month |
| **Launch** | $39 / month or $390 / year | everything in Free, plus: founding documents drafted, electronic signatures, signed PDF and Word downloads, website publishing, up to 5 companies, 5,000 AI messages a month; cancel anytime from the billing portal |

### Contracts (T-001)

```python
class PlanId(str, Enum): FREE = "free"; LAUNCH = "launch"
class BillingInterval(str, Enum): MONTH = "month"; YEAR = "year"
class Feature(str, Enum):
    DOCUMENTS = "documents"; ESIGN = "esign"; SIGNED_PDF = "signed_pdf"; WEBSITE_DEPLOY = "website_deploy"
class Plan(BaseModel):
    id: PlanId; name: str; tagline: str
    price_month_cents: int; price_year_cents: int        # 0 for free
    features: list[Feature]; max_companies: int; llm_calls_per_month: int
    highlights: list[str]                                # pricing-page bullets
PLANS: Mapping[PlanId, Plan]                             # the table above (domain/billing.py)
class Entitlements(BaseModel):
    plan: PlanId; features: frozenset[Feature]; max_companies: int; llm_calls_per_month: int
    def has(self, feature: Feature) -> bool: ...
    @classmethod
    def for_plan(cls, plan: PlanId) -> "Entitlements": ...
class SubscriptionStatus(str, Enum):
    NONE = "none"; ACTIVE = "active"; TRIALING = "trialing"; PAST_DUE = "past_due"
    CANCELED = "canceled"; INCOMPLETE = "incomplete"
class Subscription(BaseModel):
    user_id: str; plan: PlanId = PlanId.FREE; interval: BillingInterval | None = None
    status: SubscriptionStatus = SubscriptionStatus.NONE
    current_period_end: datetime | None = None; cancel_at_period_end: bool = False
    provider_customer_id: str | None = None; provider_subscription_id: str | None = None
class EntitlementsProvider(Protocol):
    def for_user(self, user_id: str | None) -> Entitlements: ...      # None -> FREE
class StaticEntitlements:   # fake: StaticEntitlements(PlanId.LAUNCH) returns that plan for everyone
class CheckoutSession(BaseModel): id: str; url: str
class PaymentEvent(BaseModel):
    id: str; type: str                                   # Stripe event type
    customer_id: str | None = None; subscription_id: str | None = None
    client_reference_id: str | None = None               # our user id
    price_id: str | None = None; status: SubscriptionStatus | None = None
    current_period_end: datetime | None = None; cancel_at_period_end: bool = False
class PaymentGateway(Protocol):
    name: str; live: bool                                # live == using sk_live_ keys
    def create_customer(self, *, email: str, user_id: str) -> str: ...
    def create_checkout_session(self, *, customer_id: str, price_id: str, user_id: str,
                                success_url: str, cancel_url: str) -> CheckoutSession: ...
    def create_portal_session(self, *, customer_id: str, return_url: str) -> str: ...
    def parse_webhook(self, payload: bytes, signature_header: str | None) -> PaymentEvent: ...  # WebhookSignatureError
class FakePaymentGateway:   # name "fake", live False; checkout url = f"{base_url}/app/billing/test-checkout?session={id}";
                            # complete_checkout(session_id) -> PaymentEvent and cancel(customer_id) -> PaymentEvent
                            # produce the same events Stripe would; parse_webhook accepts its own signed JSON
```

### Billing service (`billing/`, T-029)

```python
class BillingService:
    def __init__(self, billing: BillingRepository, accounts: AccountsRepository,
                 gateway: PaymentGateway, settings: Settings, *, clock=utcnow) -> None
    def plans(self) -> list[Plan]
    def subscription(self, user: User) -> Subscription
    def start_checkout(self, user: User, plan: PlanId, interval: BillingInterval) -> CheckoutSession
    def portal_url(self, user: User) -> str                             # ConflictError if never subscribed
    def handle_webhook(self, payload: bytes, signature_header: str | None) -> None   # idempotent
    def complete_test_checkout(self, session_id: str) -> None           # fake gateway only, else ForbiddenError
class DbEntitlements:   # EntitlementsProvider over the subscriptions table
def price_id_for(settings: Settings, plan: PlanId, interval: BillingInterval) -> str
```

- **Checkout:** creates (once) a Stripe customer for the user, then a Checkout Session in
  `subscription` mode with `client_reference_id = user.id`, success URL
  `/app/settings/billing?checkout=success`, cancel URL `/pricing?checkout=cancelled`.
  Receipts: Stripe emails receipts (enabled in the Stripe dashboard); invoices,
  payment-method changes and cancellation live in the Stripe customer portal.
- **Webhook** `POST /api/billing/webhook`: signature verified with `STRIPE_WEBHOOK_SECRET`;
  each event id is recorded in `billing_events` first and processed once.
  Handled: `checkout.session.completed`, `customer.subscription.created|updated|deleted`,
  `invoice.paid`, `invoice.payment_failed`. The subscription row is the only source of the
  user's plan.
- **Entitlements:** `ACTIVE`, `TRIALING` and `PAST_DUE` (Stripe is retrying the card) ->
  the subscribed plan; anything else -> Free. Canceling keeps the plan until
  `current_period_end` (Stripe sends the final `deleted` event then).
- **What a company gets** is the entitlement of its **billing user** (its creator), so
  an invited co-founder signs and publishes within that company without paying.
- **Gates** (services call `access.require_feature`): drafting documents (`DOCUMENTS`),
  signing and editing (`ESIGN`), PDF/Word download (`SIGNED_PDF`), publishing the website
  (`WEBSITE_DEPLOY`); creating a company beyond `max_companies` raises `PlanRequiredError`.
  Already-executed documents stay downloadable after a downgrade; nothing is deleted.
- Mode: `payments_provider=fake` in development and tests (the in-app "test checkout"
  page stands in for Stripe), Stripe **test** keys (`sk_test_...`) for staging, live keys
  only in production. `GET /api/config` tells the UI whether payments are in test mode,
  and the UI shows a "Test mode" badge on pricing and billing pages.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Stripe Checkout + portal behind a port, plans as data (chosen) | PCI scope stays with Stripe; receipts, cancellation, invoices for free; prices are config | Webhook endpoint must be reachable |
| B. Stripe Elements embedded form | Branded checkout | More PCI and UI work; needs Stripe npm packages |
| C. Paddle / Lemon Squeezy (merchant of record) | They handle sales tax | Not what the brief names |

## Consequences

- The owner needs a Stripe account, two Price ids (monthly, yearly) per paid plan, a
  webhook endpoint secret and receipts switched on in Stripe.
- Changing prices = new Stripe prices + new env values + the `PLANS` table (one file).
