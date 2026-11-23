"""T-006: Law Agent issue spotting, Q&A, draft requests, error handling and fake handlers
(ADR-0009, ADR-0010). Every LLM call goes through ``FakeLLM``; no network."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from launch_agents.agents import AgentContext, AgentServices, Specialist
from launch_agents.agents.law import LawAgent, LawIntent, spot_legal_issues
from launch_agents.agents.law.agent import APOLOGY, with_notice
from launch_agents.agents.law.fake import FAKE_HANDLERS, fake_law_answer, fake_law_intent
from launch_agents.agents.law.topics import TOPICS
from launch_agents.domain import (
    LEGAL_NOTICE,
    AgentId,
    CaseState,
    DomainCheck,
    DomainStatus,
    DraftDocuments,
    EntityType,
    LLMOutputError,
    MessageKind,
    MessageRole,
    NameCandidate,
    OpenView,
    deadline_83b,
)
from launch_agents.llm import FakeLLM
from launch_agents.llm.provider import LLMRequest
from launch_agents.ports import FakeDomainChecker

TODAY = date(2026, 11, 23)
CHECKED = datetime(2026, 11, 23, 9, 0, tzinfo=timezone.utc)


def ctx_for(facts, text, *, llm=None, state=None, today=TODAY, history=None):
    return AgentContext(
        case_id="case_test", facts=facts, state=state or CaseState(active_agent=AgentId.LAW),
        history=history or [], founder_text=text, founder_id="f1", today=today,
        llm=llm or FakeLLM(), services=AgentServices(domain_checker=FakeDomainChecker()),
    )


@pytest.fixture
def unequal_facts(sample_facts):
    founders = [sample_facts.founders[0],
                sample_facts.founders[1].model_copy(update={"vesting_months": 24, "cliff_months": 6})]
    return sample_facts.model_copy(update={"founders": founders})


def candidate(name: str, com: DomainStatus) -> NameCandidate:
    label = name.lower().replace(" ", "")
    return NameCandidate(
        name=name, rationale="fits",
        domains=[DomainCheck(domain=f"{label}.com", status=com, source="fake", checked_at=CHECKED),
                 DomainCheck(domain=f"{label}.io", status=DomainStatus.AVAILABLE, source="fake",
                             checked_at=CHECKED)],
        state_check=None, trademark_search_url="https://tmsearch.uspto.gov/search/search-information",
    )


def codes(issues):
    return [i.code for i in issues]


# --- criterion 1: spot_legal_issues -------------------------------------------------------
def test_clean_sample_has_no_issues(sample_facts):
    assert spot_legal_issues(sample_facts, CaseState(), TODAY) == []


def test_unequal_vesting(unequal_facts):
    issues = spot_legal_issues(unequal_facts, CaseState(), TODAY)
    assert codes(issues) == ["unequal_vesting"]
    message = issues[0].message
    assert "Alice Chen" in message and "Bob Diaz" in message and "different vesting schedules" in message
    assert "24 months with a 6-month cliff" in message


def test_default_vesting_counts_as_48_12(sample_facts):
    # Bob has no vesting stated: the 48/12 default equals Alice's schedule (ADR-0013).
    assert sample_facts.founders[1].vesting_months is None
    assert "unequal_vesting" not in codes(spot_legal_issues(sample_facts, CaseState(), TODAY))


def test_no_cliff_per_founder(sample_facts):
    founders = [f.model_copy(update={"vesting_months": 48, "cliff_months": 0}) for f in sample_facts.founders]
    issues = spot_legal_issues(sample_facts.model_copy(update={"founders": founders}), CaseState(), TODAY)
    assert codes(issues) == ["no_cliff", "no_cliff"]
    assert "Alice Chen" in issues[0].message and "Bob Diaz" in issues[1].message


def test_fully_vested_founder_is_not_a_no_cliff_issue(sample_facts):
    founders = [f.model_copy(update={"vesting_months": 0, "cliff_months": 0}) for f in sample_facts.founders]
    assert spot_legal_issues(sample_facts.model_copy(update={"founders": founders}), CaseState(), TODAY) == []


def test_name_conflict_for_candidates(sample_facts):
    state = CaseState(name_candidates=[candidate("Crumb Ledger", DomainStatus.TAKEN),
                                       candidate("Oven Books", DomainStatus.AVAILABLE)])
    issues = spot_legal_issues(sample_facts, state, TODAY)
    assert codes(issues) == ["name_conflict"]
    assert issues[0].severity == "warning"
    assert '"Crumb Ledger"' in issues[0].message and "Oven Books" not in issues[0].message
    assert "trademark" in issues[0].message


def test_name_conflict_for_chosen_name(sample_facts):
    state = CaseState(name_candidates=[candidate("Crumb Ledger", DomainStatus.AVAILABLE),
                                       candidate("Oven Books", DomainStatus.TAKEN)])
    chosen_ok = sample_facts.model_copy(update={"company_name": "Crumb Ledger"})
    assert spot_legal_issues(chosen_ok, state, TODAY) == []  # other candidates no longer matter
    chosen_taken = sample_facts.model_copy(update={"company_name": "Oven Books"})
    issues = spot_legal_issues(chosen_taken, state, TODAY)
    assert codes(issues) == ["name_conflict"]
    assert "Oven Books" in issues[0].message and "ovenbooks.com" in issues[0].message


def test_name_conflict_for_chosen_name_matched_by_domain(sample_facts):
    state = CaseState(name_candidates=[candidate("Oven Books", DomainStatus.TAKEN)])
    chosen = sample_facts.model_copy(update={"company_name": "Oven Books LLC"})
    assert codes(spot_legal_issues(chosen, state, TODAY)) == ["name_conflict"]


@pytest.mark.parametrize("days_left, expected", [
    (8, []), (7, ["deadline_83b_soon"]), (1, ["deadline_83b_soon"]), (0, ["deadline_83b_soon"]),
    (-1, ["deadline_83b_passed"]), (-40, ["deadline_83b_passed"]),
])
def test_83b_deadline_issues(sample_facts, days_left, expected):
    deadline = deadline_83b(sample_facts.incorporation_date)
    issues = spot_legal_issues(sample_facts, CaseState(), deadline - timedelta(days=days_left))
    assert codes(issues) == expected
    for issue in issues:
        assert issue.severity == "warning"
        assert "December 31, 2026" in issue.message


def test_no_deadline_issue_without_incorporation_date(sample_facts):
    facts = sample_facts.model_copy(update={"incorporation_date": None})
    assert spot_legal_issues(facts, CaseState(), date(2030, 1, 1)) == []


def test_issue_messages_are_founder_friendly(unequal_facts):
    founders = [unequal_facts.founders[0].model_copy(update={"cliff_months": 0}), unequal_facts.founders[1]]
    facts = unequal_facts.model_copy(update={"founders": founders, "company_name": "Oven Books"})
    state = CaseState(name_candidates=[candidate("Oven Books", DomainStatus.TAKEN)])
    issues = spot_legal_issues(facts, state, date(2026, 12, 28))
    assert codes(issues) == ["unequal_vesting", "no_cliff", "name_conflict", "deadline_83b_soon"]
    for issue in issues:
        assert issue.code not in issue.message and "_" not in issue.message
        assert "{" not in issue.message and "None" not in issue.message
        assert issue.message[0].isupper() and issue.message.endswith(".")


# --- criterion 2: questions ---------------------------------------------------------------
def test_question_is_answered_with_notice(sample_facts):
    llm = FakeLLM()
    reply = LawAgent().handle(ctx_for(sample_facts, "LLC or C-Corp?", llm=llm))
    assert len(reply.messages) == 1
    message = reply.messages[0]
    assert message.role == MessageRole.AGENT and message.agent == AgentId.LAW and message.kind == MessageKind.TEXT
    assert message.content.endswith(LEGAL_NOTICE)
    assert message.content.count(LEGAL_NOTICE) == 1
    assert "LLC" in message.content and "Delaware C-Corp" in message.content
    assert not message.content.lstrip().startswith("{")
    assert reply.hand_back is False and reply.actions == []
    assert reply.state is not None and reply.state.legal_issues == []
    assert [c.task for c in llm.calls] == ["law.intent", "law.answer"]
    assert llm.calls[0].context == {"text": "LLC or C-Corp?"}


def test_answer_context_matches_the_contract(unequal_facts):
    llm = FakeLLM()
    LawAgent().handle(ctx_for(unequal_facts, "is unequal vesting a problem?", llm=llm))
    context = llm.calls[1].context
    assert set(context) == {"text", "topic", "entity_type", "state", "founders", "issues", "deadline_83b"}
    assert context["topic"] == "vesting"
    assert context["entity_type"] == "LLC" and context["state"] == "WY"
    assert context["deadline_83b"] == "2026-12-31"
    assert context["founders"] == [
        {"name": "Alice Chen", "equity_percent": "60", "vesting_months": 48, "cliff_months": 12},
        {"name": "Bob Diaz", "equity_percent": "40", "vesting_months": 24, "cliff_months": 6},
    ]
    assert len(context["issues"]) == 1 and "different vesting schedules" in context["issues"][0]
    # the prompt carries the same facts as the context (ADR-0010)
    prompt = "\n".join(m.content for m in llm.calls[1].messages)
    assert "2026-12-31" in prompt and "Bob Diaz" in prompt and "different vesting schedules" in prompt


def test_answer_mentions_relevant_issues_and_updates_state(unequal_facts):
    reply = LawAgent().handle(ctx_for(unequal_facts, "is unequal vesting a problem?"))
    content = reply.messages[0].content
    issue = spot_legal_issues(unequal_facts, CaseState(), TODAY)[0]
    assert issue.message in content
    assert "Bob Diaz vests over 24 months with a 6-month cliff" in content
    assert reply.state.legal_issues == [issue]
    assert content.endswith(LEGAL_NOTICE) and reply.hand_back is False


def test_info_issue_not_repeated_on_unrelated_topic_but_warnings_always_are(unequal_facts):
    state = CaseState(name_candidates=[candidate("Crumb Ledger", DomainStatus.TAKEN)])
    reply = LawAgent().handle(ctx_for(unequal_facts, "LLC or C-Corp?", state=state))
    content = reply.messages[0].content
    assert "different vesting schedules" not in content  # info, other topic
    assert "Crumb Ledger" in content  # warning
    assert codes(reply.state.legal_issues) == ["unequal_vesting", "name_conflict"]


def test_83b_question_names_the_deadline(sample_facts):
    reply = LawAgent().handle(ctx_for(sample_facts, "what is an 83(b)?"))
    assert "83(b) election" in reply.messages[0].content and "December 31, 2026" in reply.messages[0].content


def test_model_written_notice_is_not_doubled(sample_facts):
    llm = FakeLLM()
    llm.script("law.answer", [f"An LLC is simple.\n\n{LEGAL_NOTICE}"])
    reply = LawAgent().handle(ctx_for(sample_facts, "LLC?", llm=llm))
    assert reply.messages[0].content == f"An LLC is simple.\n\n{LEGAL_NOTICE}"
    assert with_notice("") == LEGAL_NOTICE


# --- criterion 3: draft requests ----------------------------------------------------------
def test_draft_request_with_locked_facts(sample_facts):
    state = CaseState(active_agent=AgentId.LAW, facts_locked=True, facts_locked_at=CHECKED)
    reply = LawAgent().handle(ctx_for(sample_facts, "Please draft our documents", state=state))
    assert [a.model_dump() for a in reply.actions] == [DraftDocuments().model_dump(),
                                                       OpenView(view="legal").model_dump()]
    assert reply.hand_back is True
    assert len(reply.messages) == 1
    content = reply.messages[0].content
    assert "preparing your founding documents" in content and "Operating Agreement Summary" in content
    assert "December 31, 2026" in content
    assert content.endswith(LEGAL_NOTICE)


def test_draft_request_for_ccorp_names_the_bylaws(sample_facts):
    facts = sample_facts.model_copy(update={"entity_type": EntityType.C_CORP, "state": "DE"})
    state = CaseState(facts_locked=True)
    reply = LawAgent().handle(ctx_for(facts, "prepare the paperwork", state=state))
    assert "Bylaws Summary" in reply.messages[0].content and len(reply.actions) == 2


def test_draft_request_with_unlocked_facts(sample_facts):
    llm = FakeLLM()
    reply = LawAgent().handle(ctx_for(sample_facts, "Can you draft the documents?", llm=llm))
    assert reply.actions == []
    assert reply.hand_back is True
    content = reply.messages[0].content
    assert "Manager" in content and "confirm" in content
    assert content.endswith(LEGAL_NOTICE)
    assert [c.task for c in llm.calls] == ["law.intent"]


def test_draft_reply_lists_warnings(sample_facts):
    state = CaseState(facts_locked=True)
    reply = LawAgent().handle(ctx_for(sample_facts, "draft please", state=state, today=date(2026, 12, 29)))
    assert "only 2 days away" in reply.messages[0].content
    assert codes(reply.state.legal_issues) == ["deadline_83b_soon"]


# --- criterion 7: LLM failures ------------------------------------------------------------
def test_invalid_intent_output_becomes_apology(sample_facts):
    llm = FakeLLM()
    llm.script("law.intent", ['{"intent": "sing"}'])
    reply = LawAgent().handle(ctx_for(sample_facts, "LLC or C-Corp?", llm=llm))
    assert len(reply.messages) == 1 and reply.messages[0].agent == AgentId.LAW
    assert reply.messages[0].content == f"{APOLOGY}\n\n{LEGAL_NOTICE}"
    assert reply.actions == [] and reply.hand_back is False


def test_answer_failure_becomes_apology(unequal_facts):
    llm = FakeLLM()

    def broken(request):
        raise LLMOutputError("provider down")

    llm.register("law.answer", broken)
    reply = LawAgent().handle(ctx_for(unequal_facts, "what is vesting?", llm=llm))
    assert reply.messages[0].content.startswith("Sorry")
    assert reply.messages[0].content.endswith(LEGAL_NOTICE)
    assert codes(reply.state.legal_issues) == ["unequal_vesting"]


def test_empty_answer_becomes_apology(sample_facts):
    llm = FakeLLM()
    llm.script("law.answer", ["   "])
    reply = LawAgent().handle(ctx_for(sample_facts, "what is vesting?", llm=llm))
    assert reply.messages[0].content.startswith("Sorry")


# --- criterion 8: fake handlers -----------------------------------------------------------
def _req(task, **context):
    return LLMRequest(task=task, messages=[], context=context)


def test_fake_handlers_are_registered_for_both_tasks():
    assert set(FAKE_HANDLERS) == {"law.intent", "law.answer"}
    # the default FakeLLM picks them up (ADR-0010)
    assert FakeLLM().complete_json(_req("law.intent", text="draft it"), LawIntent).intent == "draft_documents"


@pytest.mark.parametrize("text", ["Please draft our docs", "Can you do the documents?",
                                  "Time for the paperwork", "Prepare everything we need to sign"])
def test_fake_intent_draft_keywords(text):
    assert fake_law_intent(_req("law.intent", text=text)) == {"intent": "draft_documents", "topic": None}


@pytest.mark.parametrize("text, topic", [
    ("LLC or C-Corp?", "entity_choice"), ("Which state should we pick, Delaware?", "state"),
    ("Am I personally liable if we get sued?", "liability"), ("What goes in an operating agreement?",
                                                            "operating_agreement"),
    ("How are we taxed?", "tax"), ("is unequal vesting a problem?", "vesting"),
    ("what is an 83(b)?", "83b"), ("hello there", "general"),
])
def test_fake_intent_topics(text, topic):
    assert fake_law_intent(_req("law.intent", text=text)) == {"intent": "question", "topic": topic}


def test_fake_answer_covers_every_topic_and_uses_the_facts():
    context = {"text": "?", "entity_type": "Delaware C-Corp", "state": "DE", "deadline_83b": "2026-12-31",
               "founders": [{"name": "Dana Park", "equity_percent": "100", "vesting_months": 48,
                             "cliff_months": 12}], "issues": []}
    answers = {}
    for topic in TOPICS:
        answers[topic] = fake_law_answer(_req("law.answer", topic=topic, **context))
        assert answers[topic].strip() and "{" not in answers[topic]
        assert fake_law_answer(_req("law.answer", topic=topic, **context)) == answers[topic]  # deterministic
    assert len(set(answers.values())) == len(TOPICS)
    for topic in ("entity_choice", "tax", "83b", "general"):
        assert "Delaware C-Corp" in answers[topic] and "December 31, 2026" in answers[topic], topic
    assert "Dana Park vests over 48 months with a 12-month cliff" in answers["vesting"]
    assert "bylaws" in answers["operating_agreement"]


def test_fake_answer_without_facts():
    answer = fake_law_answer(_req("law.answer", text="what is an 83(b)?", topic=None, entity_type=None,
                                  state=None, founders=[], issues=[], deadline_83b=None))
    assert "83(b)" in answer and "haven't picked an entity type" in answer


def test_law_agent_is_a_specialist():
    agent = LawAgent()
    assert isinstance(agent, Specialist) and agent.agent_id == AgentId.LAW


def test_turn_is_deterministic(unequal_facts):
    first = LawAgent().handle(ctx_for(unequal_facts, "is unequal vesting a problem?"))
    second = LawAgent().handle(ctx_for(unequal_facts, "is unequal vesting a problem?"))
    assert first == second


def test_suggests_drafting_once_facts_are_locked(sample_facts):
    reply = LawAgent().handle(ctx_for(sample_facts, "what is vesting?", state=CaseState(facts_locked=True)))
    assert [s.label for s in reply.messages[0].suggested_replies] == ["Draft our documents"]
    assert LawAgent().handle(ctx_for(sample_facts, "what is vesting?")).messages[0].suggested_replies == []


def test_sample_equity_decimal_is_plain(sample_facts):
    llm = FakeLLM()
    facts = sample_facts.model_copy(update={"founders": [sample_facts.founders[0].model_copy(
        update={"equity_percent": Decimal("60.50")}), sample_facts.founders[1]]})
    LawAgent().handle(ctx_for(facts, "vesting?", llm=llm))
    assert llm.calls[1].context["founders"][0]["equity_percent"] == "60.5"
