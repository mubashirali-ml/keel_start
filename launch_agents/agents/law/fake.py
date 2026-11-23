"""Default fake-LLM handlers for the law agent's tasks (ADR-0010). Owned by T-006.

Pure functions of the request that read ``request.context``:

- ``law.intent`` (context ``{"text"}``): keyword based. "draft", "documents", "paperwork" or
  "prepare" -> ``draft_documents``; otherwise ``question`` with a keyword topic.
- ``law.answer`` (context ``{"text", "topic", "entity_type", "state", "founders", "issues",
  "deadline_83b"}``): one paragraph for the topic, built from the case facts (it names the
  entity type, the state and the 83(b) deadline when they are known).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

from ...domain.errors import InvalidStateError
from ...domain.states import state_info
from ...llm.fake import FakeHandler
from ...llm.provider import LLMRequest
from .issues import format_date, vesting_phrase
from .topics import detect_topic, is_draft_request, normalise_topic

__all__ = ["FAKE_HANDLERS", "fake_law_answer", "fake_law_intent"]


def fake_law_intent(request: LLMRequest) -> dict[str, Any]:
    text = str(request.context.get("text", ""))
    if is_draft_request(text):
        return {"intent": "draft_documents", "topic": None}
    return {"intent": "question", "topic": detect_topic(text)}


def _state_name(code: str | None) -> str | None:
    if not code:
        return None
    try:
        return state_info(code).name
    except InvalidStateError:
        return code


def _deadline(ctx: dict[str, Any]) -> str | None:
    raw = ctx.get("deadline_83b")
    if not raw:
        return None
    try:
        return format_date(date.fromisoformat(str(raw)))
    except ValueError:
        return str(raw)


def _entity_sentence(ctx: dict[str, Any]) -> str:
    entity, state = ctx.get("entity_type"), _state_name(ctx.get("state"))
    article = "an" if entity and str(entity)[:1].upper() in "AEIOUL" else "a"  # "an LLC", "a Delaware C-Corp"
    if entity and state:
        return f"You're forming {article} **{entity}** in {state}."
    if entity:
        return f"You're forming {article} **{entity}**; the state isn't settled yet."
    return "You haven't picked an entity type yet."


def _deadline_sentence(ctx: dict[str, Any]) -> str:
    deadline = _deadline(ctx)
    if deadline:
        return f"Your 83(b) deadline is **{deadline}** (30 days after your incorporation date)."
    return "Your 83(b) deadline will be 30 days after your incorporation date, once you set one."


def _founders_sentence(ctx: dict[str, Any]) -> str:
    founders = ctx.get("founders") or []
    if not founders:
        return "Once you tell me who the founders are, I can apply this to each of you."
    parts = [f"{f['name']} vests over {vesting_phrase(int(f['vesting_months']), int(f['cliff_months']))}"
             for f in founders]
    return "In your case, " + "; ".join(parts) + "."


def _entity_choice(ctx: dict[str, Any]) -> str:
    return (
        "An **LLC** is simple and flexible: profits pass through to the owners' personal tax returns "
        "and the paperwork is light, which suits a business you plan to run and fund yourselves. A "
        "**Delaware C-Corp** is what venture investors expect: it can issue preferred stock and stock "
        "options, and its law is well known, but it pays its own corporate tax and has more formalities. "
        f"If you plan to raise outside investment, choose the C-Corp; otherwise an LLC is often enough. "
        f"{_entity_sentence(ctx)} {_deadline_sentence(ctx)}"
    )


def _state(ctx: dict[str, Any]) -> str:
    return (
        "**Delaware** is the default for companies that want venture funding: its corporate law and "
        "business court are predictable and investors know them. **Wyoming** is popular for LLCs because "
        "fees are low and owner privacy is strong. If you work from another state you will usually also "
        "register there as a foreign company and pay that state's fees. "
        f"{_entity_sentence(ctx)}"
    )


def _liability(ctx: dict[str, Any]) -> str:
    return (
        "Both an LLC and a corporation protect your personal assets: the company, not you, is "
        "responsible for its debts and lawsuits. To keep that protection, keep a separate business bank "
        "account, sign contracts in the company's name, keep the company in good standing and don't mix "
        "personal and company money. Insurance still matters for risks the company itself carries. "
        f"{_entity_sentence(ctx)}"
    )


def _operating_agreement(ctx: dict[str, Any]) -> str:
    entity = ctx.get("entity_type")
    doc = "bylaws" if entity and "Corp" in str(entity) else "operating agreement"
    return (
        f"Your {doc} sets the house rules: who owns what, how decisions are made and voted on, how "
        "profits are shared, what happens when a founder leaves, and how ownership can be transferred. "
        "Even with co-founders you trust, writing this down early prevents expensive disputes later. "
        f"I draft a plain-English summary of the {doc} from your confirmed facts, with ownership "
        f"taken from the cap table. {_entity_sentence(ctx)}"
    )


def _tax(ctx: dict[str, Any]) -> str:
    return (
        "An **LLC** is a pass-through by default: the company pays no federal income tax and each owner "
        "reports their share of the profit on their own return. A **C-Corp** pays corporate tax on its "
        "profits, and shareholders pay tax again on dividends, but founders can qualify for the QSBS "
        "exclusion on a later sale. Either way, founders with vesting equity should consider an 83(b) "
        f"election. {_entity_sentence(ctx)} {_deadline_sentence(ctx)}"
    )


def _vesting(ctx: dict[str, Any]) -> str:
    return (
        "Vesting means founders earn their equity over time, so someone who leaves early doesn't walk "
        "away with a large part of the company. The standard is 48 months with a 12-month cliff: nothing "
        "vests in the first year, a quarter vests at the cliff, then the rest monthly. Different schedules "
        "for different founders are legal, but everyone should understand and agree to them. "
        f"{_founders_sentence(ctx)} {_deadline_sentence(ctx)}"
    )


def _election_83b(ctx: dict[str, Any]) -> str:
    return (
        "An **83(b) election** is a short letter to the IRS saying you want to be taxed on your founder "
        "equity now, while it is worth almost nothing, instead of as it vests and (hopefully) grows in "
        "value. It must be mailed within 30 days of receiving the equity, with no extensions, so file it "
        f"early. {_deadline_sentence(ctx)} {_entity_sentence(ctx)} I prepare one 83(b) form per founder "
        "with your vesting terms filled in."
    )


def _general(ctx: dict[str, Any]) -> str:
    return (
        "I can help with the legal side of forming your company: choosing between an LLC and a Delaware "
        "C-Corp, the state to form in, liability protection, operating agreement basics, tax treatment, "
        "founder vesting and the 83(b) election. When your facts are confirmed I can also draft your "
        f"founding documents. {_entity_sentence(ctx)} {_deadline_sentence(ctx)}"
    )


_TOPIC_WRITERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "entity_choice": _entity_choice,
    "state": _state,
    "liability": _liability,
    "operating_agreement": _operating_agreement,
    "tax": _tax,
    "vesting": _vesting,
    "83b": _election_83b,
    "general": _general,
}


def fake_law_answer(request: LLMRequest) -> str:
    ctx = dict(request.context)
    topic = normalise_topic(ctx.get("topic"), str(ctx.get("text", "")))
    return _TOPIC_WRITERS.get(topic, _general)(ctx)


FAKE_HANDLERS: dict[str, FakeHandler] = {
    "law.intent": fake_law_intent,
    "law.answer": fake_law_answer,
}
