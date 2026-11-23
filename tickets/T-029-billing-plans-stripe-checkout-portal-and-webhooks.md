# T-029: Billing: plans, Stripe Checkout and customer portal, webhooks and entitlements

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md), [ADR-0023](../docs/adr/0023-reliability-timeouts-retries-and-failure-states.md), [ADR-0021](../docs/adr/0021-settings-environments-and-production-guards.md), [ADR-0025](../docs/adr/0025-dependency-set-v2-python-and-npm.md) |
| **Status** | todo |

## Goal

A founder can choose a plan, pay through Stripe Checkout (test mode by default, live keys
by configuration), manage or cancel it in the Stripe customer portal, and the product
always knows from verified webhooks which features each account has paid for.

## Owns (only these paths may change)

- `launch_agents/billing/`
- `launch_agents/adapters/stripe_payments.py`
- `launch_agents/persistence/billing.py`
- `tests/test_billing.py`
- `tests/test_stripe_adapter.py`
- `evidence/T-029/`
- `prs/T-029.md`

## Contracts

- **Provides:** `BillingService` (every method of ADR-0030), `DbEntitlements` (implements `EntitlementsProvider`), `price_id_for`, `StripePaymentGateway(settings, *, client=None)` (implements `PaymentGateway`), `BillingRepository`.
- **Consumes:** `Plan`, `PLANS`, `PlanId`, `BillingInterval`, `Entitlements`, `Subscription`, `SubscriptionStatus`, `CheckoutSession`, `PaymentEvent`, `PaymentGateway`, `FakePaymentGateway`, `User`, errors (T-001); `AccountsRepository` through an in-file fake in tests; package `stripe`.

## Acceptance criteria

1. `start_checkout` creates the customer once (stored), then a subscription-mode Checkout Session with the configured price id, `client_reference_id = user.id`, and the ADR-0030 success/cancel URLs; an unknown plan/interval or `FREE` -> `InvalidStateError`.
2. `portal_url` returns the portal session URL with return URL `/app/settings/billing`; never subscribed -> `ConflictError` with a friendly message.
3. `handle_webhook`: signature verified (bad signature -> `WebhookSignatureError`); each event id processed exactly once (a replay is a no-op); `checkout.session.completed`, `customer.subscription.created|updated|deleted`, `invoice.paid`, `invoice.payment_failed` update the subscription row; unknown event types are recorded and ignored.
4. `DbEntitlements.for_user`: `ACTIVE`/`TRIALING`/`PAST_DUE` -> the plan; `CANCELED`/`NONE`/`INCOMPLETE` -> Free; `cancel_at_period_end` keeps the plan until the `deleted` event; None user -> Free.
5. With `FakePaymentGateway`: full loop checkout -> `complete_test_checkout` -> Launch entitlements -> cancel -> Free; `complete_test_checkout` with a real gateway -> `ForbiddenError`.
6. `StripePaymentGateway` (tests inject a fake Stripe client object; no network): uses `max_network_retries=2` and a 20 s timeout; maps Stripe objects to `PaymentEvent`; `live` is true only for `sk_live_` keys; Stripe errors -> `PaymentProviderError` with "Payments are unavailable right now. Please try again in a minute."; keys never logged.
7. `price_id_for` reads the ADR-0021 settings; a missing price id -> `ConfigError`-style clear message (already guarded in production by T-001).
8. Repository tested on real SQLite.

## Feature run (`evidence/T-029/feature_run.py`)

With the fake gateway on a temp SQLite database: prints the plans, starts checkout for
Alice (prints the test-checkout URL), completes it (prints the webhook event, the
subscription row and Launch entitlements), replays the same event (no change), opens the
portal URL, cancels (Free entitlements), and shows a tampered webhook rejected. Then a
recorded Stripe event payload is parsed through `StripePaymentGateway` with a fake client.

## Out of scope

HTTP routes and the webhook endpoint (T-040), pricing and billing screens (T-043, T-044), feature gates in services (T-014, T-015, T-013).
