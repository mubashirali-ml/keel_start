"""Plans, entitlements and subscription types (ADR-0030 as superseded by ADR-0038).

Every number of a plan is a setting (``PLAN_*``); ``build_plans`` turns the amounts into
``Plan`` records and ``Settings.plans()`` is the only source of plans for services. ``PLANS``
holds the defaults for tests and fakes.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Mapping

from pydantic import BaseModel

__all__ = [
    "DEFAULT_PLAN_AMOUNTS",
    "PLANS",
    "BillingInterval",
    "CheckoutSession",
    "Entitlements",
    "Feature",
    "PaymentEvent",
    "Plan",
    "PlanAmounts",
    "PlanId",
    "PriceCheck",
    "SubscriptionStatus",
    "Subscription",
    "SupportLevel",
    "UsageSummary",
    "build_plans",
    "feature_required_message",
    "lowest_plan_with",
    "next_plan_for_companies",
]


class PlanId(str, Enum):
    FREE = "free"
    LAUNCH = "launch"
    TEAM = "team"


class BillingInterval(str, Enum):
    MONTH = "month"
    YEAR = "year"


class Feature(str, Enum):
    DOCUMENTS = "documents"
    ESIGN = "esign"
    SIGNED_PDF = "signed_pdf"
    WEBSITE_DEPLOY = "website_deploy"


class SupportLevel(str, Enum):
    BASIC = "basic"
    STANDARD = "standard"
    PRIORITY = "priority"


class PlanAmounts(BaseModel):
    price_month_cents: int
    price_year_cents: int
    max_companies: int
    ai_messages_per_month: int


# The ADR-0038 table (yearly = 10 x monthly, "two months free").
DEFAULT_PLAN_AMOUNTS: Mapping[PlanId, PlanAmounts] = {
    PlanId.FREE: PlanAmounts(price_month_cents=0, price_year_cents=0, max_companies=1, ai_messages_per_month=300),
    PlanId.LAUNCH: PlanAmounts(price_month_cents=2900, price_year_cents=29000, max_companies=3, ai_messages_per_month=2000),
    PlanId.TEAM: PlanAmounts(price_month_cents=7900, price_year_cents=79000, max_companies=15, ai_messages_per_month=10000),
}


class Plan(BaseModel):
    id: PlanId
    rank: int  # 0 free, 1 launch, 2 team
    name: str
    tagline: str
    price_month_cents: int
    price_year_cents: int  # 0 for free
    yearly_available: bool  # False for free or when yearly is disabled
    features: list[Feature]
    max_companies: int
    llm_calls_per_month: int
    support: SupportLevel
    support_label: str  # e.g. "Priority email, reply within 1 business day, answered first"
    highlights: list[str]  # pricing-card bullets, built from the amounts


_PAID_FEATURES = [Feature.DOCUMENTS, Feature.ESIGN, Feature.SIGNED_PDF, Feature.WEBSITE_DEPLOY]

# Static (non-numeric) parts of each plan. Support labels pending Q-009 (ADR-0038 table).
_PLAN_BASE: dict[PlanId, dict] = {
    PlanId.FREE: {
        "rank": 0,
        "name": "Free",
        "tagline": "Plan your company with every agent, free.",
        "features": [],
        "support": SupportLevel.BASIC,
        "support_label": "Help guides and email, best effort",
    },
    PlanId.LAUNCH: {
        "rank": 1,
        "name": "Launch",
        "tagline": "Form your company: documents, e-signatures and a live website.",
        "features": list(_PAID_FEATURES),
        "support": SupportLevel.STANDARD,
        "support_label": "Email, reply within 2 business days",
    },
    PlanId.TEAM: {
        "rank": 2,
        "name": "Team",
        "tagline": "For serial founders, studios and advisers who set up several companies.",
        "features": list(_PAID_FEATURES),
        "support": SupportLevel.PRIORITY,
        "support_label": "Priority email, reply within 1 business day, answered first",
    },
}


def _companies_line(n: int) -> str:
    return "1 company" if n == 1 else f"Up to {n:,} companies"


def _highlights(plan_id: PlanId, amounts: PlanAmounts, support_label: str) -> list[str]:
    common = [
        _companies_line(amounts.max_companies),
        f"{amounts.ai_messages_per_month:,} AI messages a month",
    ]
    if plan_id == PlanId.FREE:
        body = [
            "Chat with every agent, legal Q&A and name ideas with live domain checks",
            "Cap table with CSV and Excel downloads",
            "Website preview and .zip download",
            "Registration checklist and 83(b) reminders",
        ]
        lead: list[str] = []
    elif plan_id == PlanId.LAUNCH:
        body = [
            "Founding documents drafted",
            "Electronic signatures",
            "Signed PDF and Word downloads",
            "Website publishing",
        ]
        lead = ["Everything in Free"]
    else:  # Team: the same features as Launch; only limits and support differ
        body = []
        lead = ["Everything in Launch"]
    return [*lead, *common, *body, "Co-founders join free, unlimited", support_label]


def build_plans(
    amounts: Mapping[PlanId, PlanAmounts] = DEFAULT_PLAN_AMOUNTS, *, yearly_enabled: bool = True
) -> dict[PlanId, Plan]:
    """The three plans built from their amounts (ADR-0038), in rank order."""
    plans: dict[PlanId, Plan] = {}
    for plan_id in (PlanId.FREE, PlanId.LAUNCH, PlanId.TEAM):
        a = amounts.get(plan_id, DEFAULT_PLAN_AMOUNTS[plan_id])
        base = _PLAN_BASE[plan_id]
        plans[plan_id] = Plan(
            id=plan_id,
            rank=base["rank"],
            name=base["name"],
            tagline=base["tagline"],
            price_month_cents=a.price_month_cents,
            price_year_cents=a.price_year_cents,
            yearly_available=yearly_enabled and plan_id != PlanId.FREE,
            features=list(base["features"]),
            max_companies=a.max_companies,
            llm_calls_per_month=a.ai_messages_per_month,
            support=base["support"],
            support_label=base["support_label"],
            highlights=_highlights(plan_id, a, base["support_label"]),
        )
    return plans


PLANS: Mapping[PlanId, Plan] = build_plans()


def _by_rank(plans: Mapping[PlanId, Plan]) -> list[Plan]:
    return sorted(plans.values(), key=lambda p: p.rank)


def lowest_plan_with(feature: Feature, plans: Mapping[PlanId, Plan] = PLANS) -> Plan:
    """The cheapest (lowest-rank) plan that includes ``feature``."""
    for plan in _by_rank(plans):
        if feature in plan.features:
            return plan
    raise LookupError(f"no plan includes the feature {feature.value!r}")


def next_plan_for_companies(current: PlanId, plans: Mapping[PlanId, Plan] = PLANS) -> Plan | None:
    """The next plan up that allows more companies than ``current`` (Free -> Launch -> Team -> None)."""
    now = plans[current]
    for plan in _by_rank(plans):
        if plan.rank > now.rank and plan.max_companies > now.max_companies:
            return plan
    return None


_FEATURE_PHRASES: dict[Feature, tuple[str, str]] = {
    Feature.DOCUMENTS: ("Drafting founding documents", "is"),
    Feature.ESIGN: ("Electronic signatures", "are"),
    Feature.SIGNED_PDF: ("Signed PDF and Word downloads", "are"),
    Feature.WEBSITE_DEPLOY: ("Publishing your website", "is"),
}


def feature_required_message(feature: Feature, plans: Mapping[PlanId, Plan] = PLANS) -> str:
    """Friendly upgrade copy, e.g. "Publishing your website is included in the Launch and Team plans."."""
    names = [p.name for p in _by_rank(plans) if feature in p.features]
    what, verb = _FEATURE_PHRASES[feature]
    if not names:
        return f"{what} {verb} not available on any plan right now."
    if len(names) == 1:
        return f"{what} {verb} included in the {names[0]} plan."
    return f"{what} {verb} included in the {', '.join(names[:-1])} and {names[-1]} plans."


class Entitlements(BaseModel):
    plan: PlanId
    features: frozenset[Feature]
    max_companies: int
    llm_calls_per_month: int
    support: SupportLevel

    def has(self, feature: Feature) -> bool:
        return feature in self.features

    @classmethod
    def for_plan(cls, plan: PlanId, plans: Mapping[PlanId, Plan] = PLANS) -> "Entitlements":
        p = plans[plan]
        return cls(
            plan=p.id,
            features=frozenset(p.features),
            max_companies=p.max_companies,
            llm_calls_per_month=p.llm_calls_per_month,
            support=p.support,
        )


class SubscriptionStatus(str, Enum):
    NONE = "none"
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"


class Subscription(BaseModel):
    user_id: str
    plan: PlanId = PlanId.FREE
    interval: BillingInterval | None = None
    status: SubscriptionStatus = SubscriptionStatus.NONE
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None


class CheckoutSession(BaseModel):
    id: str
    url: str


class PaymentEvent(BaseModel):
    id: str
    type: str  # Stripe event type
    customer_id: str | None = None
    subscription_id: str | None = None
    client_reference_id: str | None = None  # our user id
    price_id: str | None = None
    status: SubscriptionStatus | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False


class UsageSummary(BaseModel):
    ai_messages_used: int
    ai_messages_limit: int
    resets_on: date
    companies_used: int
    companies_limit: int


class PriceCheck(BaseModel):
    plan: PlanId
    interval: BillingInterval
    price_id: str | None
    expected_cents: int
    provider_cents: int | None
    ok: bool
    problem: str | None
