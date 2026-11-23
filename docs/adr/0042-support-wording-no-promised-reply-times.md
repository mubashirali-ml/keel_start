# ADR-0042: Support wording: email support on every plan, priority on Team, no promised reply times

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor, product owner (Q-009: no promised times) |
| **Tickets** | T-047 (plan labels in `domain/billing.py`, foundation tests), T-029 (billing), T-043 (pricing and Terms), T-044 (billing settings), T-038 / T-045 (admin plan filter, unchanged) |
| **Scope** | `domain/billing.py` `_PLAN_BASE` support labels and highlights, every customer-facing mention of support |

## Context

ADR-0038 printed reply times on the pricing page and in billing settings (Free best
effort, Launch within 2 business days, Team within 1 business day), pending Q-009. The
product owner answered Q-009: **no promised support times**. Every plan says "email
support"; Team says "priority support". Nothing on the pricing page promises a reply
time. This ADR **supersedes the "Support" row of the ADR-0038 plan table and the
reply-time wording of its "Support level" bullet**. Everything else in ADR-0038 holds,
including `SupportLevel`, `Plan.support` / `support_label`, the "Contact support"
`mailto:` with the `[{Plan name}]` subject prefix, and the admin plan filter.

## Decision

- **Labels** (`Plan.support_label`, the last pricing-card highlight, the comparison
  table's support row and the billing settings):

  | Plan | `support` | `support_label` |
  |---|---|---|
  | Free | `BASIC` | "Email support" |
  | Launch | `STANDARD` | "Email support" |
  | Team | `PRIORITY` | "Priority support" |

  The enum values and the contracts do not change; only the label strings do
  (T-047 changes `_PLAN_BASE` and the foundation test that checks them).
- **No reply time anywhere a customer looks.** No customer-facing copy (pricing, billing
  settings, help menu, emails, Terms of Service, FAQ) states or implies a reply time.
  The reply-time phrases the tests look for are "reply within", "respond within",
  "response time", "business day", "same day" and "answered first" (case-insensitive). The Terms draft says
  support is offered by email on a reasonable-efforts basis, with Team requests handled
  first, and no service-level commitment. T-043 adds a test that the pricing and Terms
  pages contain none of those phrases; T-047 adds the same check over the plan labels and
  highlights.
- **What "priority" means in practice** stays internal: the owner answers Team mail
  first, using the `[Team]` subject prefix and the admin plan filter (ADR-0038). The
  pricing FAQ may say "Team requests are handled first" but gives no time.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. "Email support" everywhere, "Priority support" on Team, no times (chosen) | Owner's choice; nothing to keep up with; no contractual promise | Team's support benefit is less concrete |
| B. Best effort / 2 business days / 1 business day (old default) | Concrete selling point | A promise the owner must keep personally |
| C. Faster promises (1 day / same day) | Strongest selling point | Most work for the owner |

## Consequences

- The pricing page, billing settings and Terms carry no reply-time promise; changing
  that later is a label change in `domain/billing.py` plus the Terms text.
- Team's pitch rests on capacity (15 companies, 10,000 AI messages) plus priority
  handling.
