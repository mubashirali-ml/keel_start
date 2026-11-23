"""T-001 foundation: package layout, shared contracts, fakes, schema, stubs and app skeleton.

One section per acceptance criterion of tickets/T-001-foundation-skeleton-contracts-and-fakes.md.
Stub tests check signatures only (never ``NotImplementedError``), so they keep passing after
the owning tickets implement them.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import io
import json
import os
import pkgutil
import re
import subprocess
import sys
import zipfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

import launch_agents
from launch_agents.config import AppEnv, ConfigError, Settings, load_settings
from launch_agents.domain import (
    AGENT_PROFILES,
    DEFAULT_PLAN_AMOUNTS,
    ESIGN_CONSENT_TEXT,
    ESIGN_CONSENT_VERSION,
    PLANS,
    US_STATES,
    Actor,
    AgentId,
    AuditAction,
    AuditEntry,
    BillingInterval,
    BillingOverview,
    BuildWebsite,
    CapTable,
    CapTableRow,
    CaseAccess,
    CaseFacts,
    CaseRecord,
    CaseState,
    CaseSummary,
    CaseView,
    ChatMessage,
    CheckoutSession,
    ChooseName,
    DeployResult,
    Document,
    DocumentKind,
    DocumentStatus,
    DomainCheck,
    DomainStatus,
    DraftDocument,
    EditRequest,
    EmailMessage,
    EmailTemplate,
    Entitlements,
    EntityType,
    FactsPatch,
    Feature,
    Founder,
    FounderPatch,
    GuideLink,
    GuideStep,
    GuideView,
    InvalidStateError,
    Invite,
    JobKind,
    JobRecord,
    JobStatus,
    LaunchError,
    LegalIssue,
    LLMOutputError,
    LockFacts,
    MemberRole,
    Membership,
    MemberView,
    MessageKind,
    MessageRole,
    MeView,
    NameCandidate,
    OpenView,
    PaymentEvent,
    Permission,
    PlanId,
    PlanRequiredError,
    PostMessageResult,
    PriceCheck,
    Progress,
    PublicConfig,
    QaCheckId,
    QaCheckResult,
    QaIssue,
    QaReport,
    RegistrationGuide,
    RequestContext,
    RetryableError,
    RetryableJobError,
    SendResult,
    SignatureEvidence,
    Signature,
    SignRequest,
    SiteBuild,
    SiteBuildStatus,
    SiteBundle,
    SiteContact,
    SiteContent,
    SiteFile,
    SiteFounder,
    SitePage,
    SiteSection,
    StateNameCheck,
    StepId,
    StepProgress,
    StepStatus,
    Subscription,
    SubscriptionStatus,
    SuggestedReply,
    SupportLevel,
    UsageSummary,
    User,
    ValidationIssue,
    ValidationResult,
    VestingEvent,
    WebsitePatch,
    WebsiteRequirements,
    add_months,
    apply_patch,
    days_until,
    deadline_83b,
    document_sha256,
    domain_label,
    handoff_message,
    lowest_plan_with,
    names_match,
    new_id,
    next_plan_for_companies,
    slugify,
    state_info,
)
from launch_agents.domain import errors as errors_module
from launch_agents.llm import FakeLLM, FakeLLMMissingHandler, LLMMessage, LLMRequest, LLMUsage, get_llm, usage_sink
from launch_agents.llm.usage import report_usage
from launch_agents.ports import (
    DEFAULT_FAKE_TAKEN,
    FakeDomainChecker,
    FakeEmailSender,
    FakePaymentGateway,
    FakeSiteHost,
    InlineJobRunner,
    RecordingMailer,
    RecordingNotifier,
    StaticEntitlements,
    UnconfiguredSiteHost,
)
from launch_agents.reliability import Deadline, RetryPolicy, call_with_retry, is_transient

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = REPO_ROOT / "launch_agents"
NOW = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
ADR0025_IMPORTS = ("alembic", "psycopg", "argon2", "stripe", "reportlab", "docx", "email_validator")


def _test_env(**extra: str) -> dict[str, str]:
    return {"APP_ENV": "test", "LAUNCH_FAKE_SERVICES": "1", **extra}


# =========================================================================================
# 1. Every module of the ADR-0024 layout imports cleanly (also without the ADR-0025 packages)
# =========================================================================================
ADR0024_MODULES = [
    "config", "reliability",
    "domain", "domain.constants", "domain.types", "domain.state", "domain.messages", "domain.cap_table",
    "domain.documents", "domain.website", "domain.guide", "domain.states", "domain.helpers", "domain.errors",
    "domain.views", "domain.accounts", "domain.billing", "domain.jobs", "domain.email",
    "llm", "llm.provider", "llm.fake", "llm.usage", "llm.claude_code", "llm.anthropic_provider", "llm.openai_compat",
    "ports", "ports.domain_check", "ports.hosting", "ports.email", "ports.notifications", "ports.payments",
    "ports.entitlements", "ports.jobs",
    "adapters.rdap", "adapters.netlify", "adapters.smtp_email", "adapters.stripe_payments",
    "rules.validation", "rules.cap_table", "rules.exports", "signoff",
    "persistence.tables", "persistence.engine", "persistence.repository", "persistence.accounts", "persistence.team",
    "persistence.email_outbox", "persistence.billing", "persistence.jobs", "persistence.limits",
    "persistence.privacy", "persistence.admin",
    "accounts", "team", "access", "email", "billing", "jobs", "jobs.__main__", "pdf", "security", "observability",
    "agents.base", "agents.manager.greeting",
    *[f"agents.{a}" for a in ("manager", "law", "name", "website", "qa", "guide")],
    *[f"agents.{a}.fake" for a in ("manager", "law", "name", "website", "qa", "guide")],
    "orchestrator", "pipelines.website", "workflows.ports", "workflows.website", "workflows.case", "workflows.legal",
    "notifications", "privacy", "admin", "admin.__main__", "composition",
    "api.app", "api.errors", "api.deps", "api.middleware", "api.schemas", "api.routes",
    *[f"api.routes.{r}" for r in ("cases", "jobs", "legal", "website", "auth", "account", "team", "billing", "admin")],
    "demo", "demo.__main__", "devtools.ui_run",
]


@pytest.mark.parametrize("name", ADR0024_MODULES)
def test_adr0024_module_imports(name):
    module = importlib.import_module(f"launch_agents.{name}")
    assert module.__doc__, f"launch_agents.{name} needs a docstring citing its ADR"


def _all_package_modules() -> list[str]:
    names = ["launch_agents"]
    for info in pkgutil.walk_packages(launch_agents.__path__, "launch_agents."):
        names.append(info.name)
    return names


def test_every_module_in_the_package_imports():
    failures = {}
    for name in _all_package_modules():
        try:
            importlib.import_module(name)
        except Exception as exc:  # pragma: no cover - reported below
            failures[name] = repr(exc)
    assert failures == {}


def test_modules_import_without_the_adr0025_packages():
    """Imports of alembic, psycopg, argon2, stripe, reportlab, docx, email_validator are lazy."""
    code = (
        "import sys, importlib, pkgutil\n"
        f"for name in {ADR0025_IMPORTS!r}: sys.modules[name] = None\n"
        "import launch_agents\n"
        "names = ['launch_agents'] + [i.name for i in pkgutil.walk_packages(launch_agents.__path__, 'launch_agents.')]\n"
        "for n in names: importlib.import_module(n)\n"
        "from launch_agents.persistence.tables import metadata\n"
        "print('imported', len(names))\n"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("imported ")


def test_domain_imports_nothing_else_from_the_package():
    for path in (PACKAGE_DIR / "domain").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*from \.\.", text, re.M), f"{path.name} imports outside domain"
        assert not re.search(r"^\s*(from|import)\s+launch_agents", text, re.M), f"{path.name} imports the package"


# =========================================================================================
# 2. Domain models match the ADRs field for field and round-trip through JSON
# =========================================================================================
EXPECTED_FIELDS: dict[type[BaseModel], str] = {
    Founder: "id name email equity_percent vesting_months cliff_months",
    WebsiteRequirements: "pages services about contact_email contact_phone contact_address extra_content style_notes",
    CaseFacts: "business_description founders entity_type state incorporation_date name_preferences company_name website",
    FounderPatch: "id name email equity_percent vesting_months cliff_months",
    WebsitePatch: "pages services about contact_email contact_phone contact_address extra_content style_notes",
    FactsPatch: "business_description founders remove_founder_ids entity_type state incorporation_date name_preferences company_name website",
    ValidationIssue: "code field message founder_id",
    ValidationResult: "ok issues missing facts notes",
    DomainCheck: "domain status source checked_at detail",
    StateNameCheck: "state status search_url office_url",
    NameCandidate: "name rationale domains state_check trademark_search_url",
    LegalIssue: "code severity message",
    CaseState: "active_agent facts_locked facts_locked_at pending_fact notices_given name_candidates chosen_domain legal_issues",
    CaseRecord: "id created_at updated_at facts state created_by billing_user_id",
    SuggestedReply: "label text",
    ChatMessage: "id case_id seq role agent founder_id kind content payload suggested_replies created_at",
    VestingEvent: "month date vested_this_event cumulative_vested",
    CapTableRow: "founder_id name email equity_percent shares vesting_months cliff_months schedule",
    CapTable: "entity_type unit_label authorized vesting_start rows total_issued",
    SignatureEvidence: "user_id typed_name consent_version content_sha256 ip user_agent acted_by_user_id",
    Signature: "founder_id version signed_at user_id typed_name consent_version content_sha256 ip user_agent acted_by_user_id",
    DraftDocument: "kind title founder_id content required_signers",
    Document: "id case_id kind title founder_id version content status required_signers signatures created_at updated_at",
    AuditEntry: "id case_id document_id actor action from_version to_version detail at",
    SiteSection: "heading body items",
    SitePage: "slug title nav_label sections",
    SiteContact: "email phone address",
    SiteFounder: "name bio",
    SiteContent: "company_name tagline pages contact founders footer_note",
    SiteFile: "path content content_type",
    SiteBundle: "files",
    QaIssue: "check severity page message",
    QaCheckResult: "check label passed issues",
    QaReport: "passed round checks checked_at",
    SiteBuild: "id case_id version content bundle qa_reports qa_passed fix_rounds status deploy_url deploy_message override_by created_at updated_at",
    DeployResult: "status url deploy_id provider message",
    GuideLink: "label url",
    GuideStep: "id category title detail links fee due optional",
    RegistrationGuide: "state state_name entity_type full_guide steps last_reviewed sources disclaimer",
    StepProgress: "id label status detail",
    Progress: "steps percent",
    CaseView: "id created_at updated_at facts facts_locked active_agent company_name chosen_domain validation_issues missing_facts deadline_83b days_until_83b progress legal_issues my_role my_founder_id plan active_jobs",
    CaseSummary: "id company_name created_at updated_at percent",
    GuideView: "guide done done_count total",
    PostMessageResult: "messages case open_view jobs",
    MeView: "user plan subscription email_verified companies csrf_token",
    MemberView: "user_id full_name email role founder_id founder_name joined_at",
    PublicConfig: "brand_name demo_mode payments_test_mode hosting_configured plans esign_consent_text esign_consent_version support_email yearly_enabled",
    BillingOverview: "subscription plan usage can_switch_plan",
    SignRequest: "version content_sha256 typed_name consent",
    EditRequest: "version content_sha256 typed_name consent content",
    User: "id email full_name email_verified_at is_admin created_at",
    Membership: "case_id user_id role founder_id joined_at",
    Invite: "id case_id email founder_id invited_by created_at expires_at accepted_at revoked_at",
    Entitlements: "plan features max_companies llm_calls_per_month support",
    Subscription: "user_id plan interval status current_period_end cancel_at_period_end provider_customer_id provider_subscription_id",
    CheckoutSession: "id url",
    PaymentEvent: "id type customer_id subscription_id client_reference_id price_id status current_period_end cancel_at_period_end",
    UsageSummary: "ai_messages_used ai_messages_limit resets_on companies_used companies_limit",
    PriceCheck: "plan interval price_id expected_cents provider_cents ok problem",
    JobRecord: "id kind status case_id user_id payload result error attempts max_attempts run_at created_at updated_at finished_at",
    EmailMessage: "to subject text html template",
    SendResult: "ok provider_id error transient",
    LLMMessage: "role content",
    LLMRequest: "task messages context temperature max_tokens",
    LLMUsage: "provider model task input_tokens output_tokens duration_ms ok",
}


def _plan_fields() -> str:
    return ("id rank name tagline price_month_cents price_year_cents yearly_available features max_companies "
            "llm_calls_per_month support support_label highlights")


@pytest.mark.parametrize("model", list(EXPECTED_FIELDS), ids=lambda m: m.__name__)
def test_model_fields_match_the_adrs(model):
    assert list(model.model_fields) == EXPECTED_FIELDS[model].split()


def test_plan_and_amount_fields_match_adr0038():
    from launch_agents.domain import Plan, PlanAmounts

    assert list(Plan.model_fields) == _plan_fields().split()
    assert list(PlanAmounts.model_fields) == "price_month_cents price_year_cents max_companies ai_messages_per_month".split()


EXPECTED_DATACLASS_FIELDS = {
    RequestContext: "request_id user ip user_agent demo_mode act_as_founder_id",
    Actor: "kind user_id founder_id ip user_agent request_id acted_by_user_id",
    CaseAccess: "case_id actor membership permissions entitlements billing_user_id",
}


@pytest.mark.parametrize("cls", list(EXPECTED_DATACLASS_FIELDS), ids=lambda c: c.__name__)
def test_dataclass_fields_match_adr0026(cls):
    assert [f.name for f in dataclasses.fields(cls)] == EXPECTED_DATACLASS_FIELDS[cls].split()
    assert cls.__dataclass_params__.frozen


def test_agent_and_job_dataclasses():
    from launch_agents.agents.base import AgentContext, AgentDeps, AgentServices
    from launch_agents.domain import JobContext

    assert [f.name for f in dataclasses.fields(AgentServices)] == ["domain_checker"]
    assert [f.name for f in dataclasses.fields(AgentContext)] == (
        "case_id facts state history founder_text founder_id today llm services".split()
    )
    assert [f.name for f in dataclasses.fields(AgentDeps)] == ["llm", "services", "specialists"]
    assert [f.name for f in dataclasses.fields(JobContext)] == ["job", "attempt", "now"]


EXPECTED_ENUMS: dict[type[Enum], list[str]] = {
    EntityType: ["LLC", "Delaware C-Corp"],
    DomainStatus: ["available", "taken", "unknown"],
    AgentId: ["manager", "law", "name", "website", "qa", "guide", "cap_table", "signoff"],
    MessageRole: ["founder", "agent", "system"],
    MessageKind: ["text", "handoff", "notice", "validation", "name_options", "documents_ready", "cap_table_ready",
                  "site_preview", "qa_report", "deploy_status", "guide_ready"],
    DocumentKind: ["ip_assignment", "bylaws_summary", "operating_agreement_summary", "election_83b"],
    DocumentStatus: ["awaiting_signatures", "executed"],
    AuditAction: ["created", "signed", "edited", "signatures_invalidated", "executed", "reopened", "regenerated",
                  "rejected_stale", "rejected_not_signer", "rejected_already_signed", "legal_complete", "facts_locked",
                  "name_chosen", "checklist_updated", "site_built", "site_deployed", "deploy_override",
                  "pdf_downloaded", "member_joined", "invite_sent", "plan_changed"],
    QaCheckId: ["pages_present", "content_present", "company_name", "contact_details", "internal_links", "image_alt",
                "headings", "html_structure", "contrast", "requirements_review"],
    SiteBuildStatus: ["qa_passed", "qa_failed", "deployed", "deploy_failed", "deploy_not_configured"],
    StepId: ["facts", "name", "legal", "cap_table", "website", "registration"],
    StepStatus: ["not_started", "in_progress", "done", "attention"],
    MemberRole: ["owner", "member"],
    Permission: ["view", "chat", "sign", "edit_documents", "build_website", "deploy", "tick_guide", "manage_team",
                 "delete_company"],
    PlanId: ["free", "launch", "team"],
    BillingInterval: ["month", "year"],
    Feature: ["documents", "esign", "signed_pdf", "website_deploy"],
    SupportLevel: ["basic", "standard", "priority"],
    SubscriptionStatus: ["none", "active", "trialing", "past_due", "canceled", "incomplete"],
    JobStatus: ["queued", "running", "succeeded", "failed", "cancelled"],
    EmailTemplate: ["verify_email", "password_reset", "invite_cofounder", "signature_needed", "document_executed",
                    "deadline_83b_reminder"],
}


@pytest.mark.parametrize("enum", list(EXPECTED_ENUMS), ids=lambda e: e.__name__)
def test_enum_values_match_the_adrs(enum):
    assert [m.value for m in enum] == EXPECTED_ENUMS[enum]


def test_job_kinds_and_constants():
    from launch_agents.domain import constants as c

    assert (JobKind.WEBSITE_BUILD, JobKind.WEBSITE_DEPLOY, JobKind.EMAIL_SEND, JobKind.REMINDERS_SWEEP) == (
        "website.build", "website.deploy", "email.send", "reminders.sweep")
    assert (c.AUTHORIZED_SHARES, c.DEFAULT_VESTING_MONTHS, c.DEFAULT_CLIFF_MONTHS, c.ELECTION_83B_DAYS,
            c.MAX_QA_FIX_ROUNDS, c.EQUITY_DECIMALS) == (10_000_000, 48, 12, 30, 2, 2)
    assert c.DOMAIN_TLDS == (".com", ".co", ".io")
    assert c.FULL_GUIDE_STATES == ("DE", "WY")
    assert c.DEFAULT_SITE_PAGES == ("Home", "About", "Services", "Contact")
    assert c.LEGAL_NOTICE.startswith("This is not legal advice.")
    assert c.USPTO_TRADEMARK_SEARCH_URL == "https://tmsearch.uspto.gov/search/search-information"
    assert c.BRAND_NAME == "Charterly"
    assert ESIGN_CONSENT_VERSION == "2026-11-23"
    assert ESIGN_CONSENT_TEXT.startswith("I agree to sign this document electronically.")


def _samples(sample_facts) -> list[BaseModel]:
    check = DomainCheck(domain="crumbledger.com", status=DomainStatus.TAKEN, source="fake", checked_at=NOW)
    candidate = NameCandidate(
        name="Crumb Ledger", rationale="bakery + books", domains=[check],
        state_check=StateNameCheck(state="WY", search_url="https://a.example", office_url="https://b.example"),
        trademark_search_url="https://tm.example",
    )
    state = CaseState(active_agent=AgentId.LAW, facts_locked=True, facts_locked_at=NOW, pending_fact="state",
                      notices_given=["default_vesting:f2"], name_candidates=[candidate], chosen_domain="crumbledger.io",
                      legal_issues=[LegalIssue(code="deadline_83b", severity="warning", message="File soon.")])
    signature = Signature(founder_id="f1", version=2, signed_at=NOW, user_id="usr_1", typed_name="Alice Chen",
                          consent_version=ESIGN_CONSENT_VERSION, content_sha256="ab" * 32, ip="127.0.0.1",
                          user_agent="pytest", acted_by_user_id=None)
    document = Document(id="doc_1", case_id="case_1", kind=DocumentKind.ELECTION_83B, title="IRS 83(b) Election",
                        founder_id="f1", version=2, content="# 83(b)\n", status=DocumentStatus.EXECUTED,
                        required_signers=["f1"], signatures=[signature], created_at=NOW, updated_at=NOW)
    report = QaReport(passed=False, round=1, checked_at=NOW, checks=[
        QaCheckResult(check=QaCheckId.PAGES_PRESENT, label="Pages", passed=False,
                      issues=[QaIssue(check=QaCheckId.PAGES_PRESENT, severity="error", page="about", message="Missing")])])
    content = SiteContent(company_name="Crumb Ledger", tagline="Books for bakers",
                          pages=[SitePage(slug="index", title="Home", nav_label="Home",
                                          sections=[SiteSection(heading="Hi", body="Welcome", items=["a"])])],
                          contact=SiteContact(email="hi@crumb.test"), founders=[SiteFounder(name="Alice", bio="Baker")])
    bundle = SiteBundle(files=[SiteFile(path="index.html", content="<!doctype html>", content_type="text/html")])
    build = SiteBuild(id="site_1", case_id="case_1", version=1, content=content, bundle=bundle, qa_reports=[report],
                      qa_passed=False, fix_rounds=1, status=SiteBuildStatus.QA_FAILED, created_at=NOW, updated_at=NOW)
    job = JobRecord(id="job_1", kind=JobKind.WEBSITE_BUILD, status=JobStatus.SUCCEEDED, case_id="case_1",
                    payload={"case_id": "case_1"}, result={"build_id": "site_1"}, attempts=1, run_at=NOW,
                    created_at=NOW, updated_at=NOW, finished_at=NOW)
    user = User(id="usr_1", email="alice@example.com", full_name="Alice Chen", email_verified_at=NOW, created_at=NOW)
    progress = Progress(steps=[StepProgress(id=StepId.FACTS, label="Facts", status=StepStatus.DONE, detail="Locked")],
                        percent=16)
    view = CaseView(id="case_1", created_at=NOW, updated_at=NOW, facts=sample_facts, facts_locked=True,
                    active_agent=AgentId.MANAGER, company_name="Crumb Ledger", chosen_domain=None,
                    validation_issues=[ValidationIssue(code="equity_total", field="founders", message="x")],
                    missing_facts=[], deadline_83b=date(2026, 12, 31), days_until_83b=38, progress=progress,
                    legal_issues=[], my_role=MemberRole.OWNER, my_founder_id="f1", plan=PlanId.LAUNCH, active_jobs=[job])
    summary = CaseSummary(id="case_1", company_name=None, created_at=NOW, updated_at=NOW, percent=0)
    subscription = Subscription(user_id="usr_1", plan=PlanId.TEAM, interval=BillingInterval.YEAR,
                                status=SubscriptionStatus.ACTIVE, current_period_end=NOW, provider_customer_id="cus_1")
    guide = RegistrationGuide(state="WY", state_name="Wyoming", entity_type=EntityType.LLC, full_guide=True,
                              steps=[GuideStep(id="83b-mail", category="83b", title="Mail", detail="x",
                                               links=[GuideLink(label="IRS", url="https://irs.gov")], fee="$0",
                                               due=date(2026, 12, 31))],
                              last_reviewed=date(2026, 11, 1), sources=[], disclaimer="Not legal advice.")
    message = handoff_message(AgentId.MANAGER, AgentId.LAW, direction="handover", reason="legal question")
    return [
        sample_facts,
        FactsPatch(founders=[FounderPatch(name="Cara", equity_percent=Decimal("12.5"))], remove_founder_ids=["f2"],
                   website=WebsitePatch(pages=["Home"])),
        message,
        state,
        CaseRecord(id="case_1", created_at=NOW, updated_at=NOW, facts=sample_facts, state=state, created_by="usr_1",
                   billing_user_id="usr_1"),
        ValidationResult(ok=False, issues=[ValidationIssue(code="c", field="f", message="m", founder_id="f1")],
                         missing=["state"], facts=sample_facts, notes=["n"]),
        CapTable(entity_type=EntityType.LLC, unit_label="units", vesting_start=date(2026, 12, 1), total_issued=10_000_000,
                 rows=[CapTableRow(founder_id="f1", name="Alice", email="a@x.test", equity_percent=Decimal("60"),
                                   shares=6_000_000, vesting_months=48, cliff_months=12,
                                   schedule=[VestingEvent(month=12, date=date(2027, 12, 1), vested_this_event=1_500_000,
                                                          cumulative_vested=1_500_000)])]),
        document,
        DraftDocument(kind=DocumentKind.IP_ASSIGNMENT, title="IP", founder_id=None, content="x", required_signers=["f1", "f2"]),
        AuditEntry(id=3, case_id="case_1", document_id="doc_1", actor="f1", action=AuditAction.SIGNED, from_version=1,
                   to_version=1, detail={"ip": "127.0.0.1"}, at=NOW),
        SignatureEvidence(user_id="usr_1", typed_name="Alice Chen", consent_version=ESIGN_CONSENT_VERSION,
                          content_sha256="cd" * 32),
        build,
        DeployResult(status="deployed", url="https://x.fake-host.test", deploy_id="d1", provider="fake", message="ok"),
        guide,
        GuideView(guide=guide, done={"83b-mail": True}, done_count=1, total=1),
        view,
        summary,
        PostMessageResult(messages=[message], case=view, open_view="legal", jobs=[job]),
        MeView(user=user, plan=PlanId.TEAM, subscription=subscription, email_verified=True, companies=[summary],
               csrf_token="tok"),
        MemberView(user_id="usr_1", full_name="Alice", email="a@x.test", role=MemberRole.OWNER, founder_id="f1",
                   founder_name="Alice", joined_at=NOW),
        PublicConfig(brand_name="Charterly", demo_mode=False, payments_test_mode=True, hosting_configured=False,
                     plans=list(PLANS.values()), esign_consent_text=ESIGN_CONSENT_TEXT,
                     esign_consent_version=ESIGN_CONSENT_VERSION, support_email=None, yearly_enabled=True),
        BillingOverview(subscription=subscription, plan=PLANS[PlanId.TEAM], can_switch_plan=True,
                        usage=UsageSummary(ai_messages_used=5, ai_messages_limit=10_000, resets_on=date(2026, 12, 1),
                                           companies_used=1, companies_limit=15)),
        SignRequest(version=1, content_sha256="ab" * 32, typed_name="Alice Chen", consent=True),
        EditRequest(version=1, content_sha256="ab" * 32, typed_name="Alice Chen", consent=True, content="new"),
        user,
        Membership(case_id="case_1", user_id="usr_1", role=MemberRole.MEMBER, founder_id="f2", joined_at=NOW),
        Invite(id="inv_1", case_id="case_1", email="bob@example.com", founder_id="f2", invited_by="usr_1",
               created_at=NOW, expires_at=NOW + timedelta(days=7)),
        Entitlements.for_plan(PlanId.LAUNCH),
        subscription,
        CheckoutSession(id="cs_1", url="https://x.test"),
        PaymentEvent(id="evt_1", type="checkout.session.completed", status=SubscriptionStatus.ACTIVE, current_period_end=NOW),
        PriceCheck(plan=PlanId.LAUNCH, interval=BillingInterval.MONTH, price_id="price_1", expected_cents=2900,
                   provider_cents=2900, ok=True, problem=None),
        job,
        EmailMessage(to="a@x.test", subject="s", text="t", html="<p>t</p>", template=EmailTemplate.VERIFY_EMAIL),
        SendResult(ok=False, error="later", transient=True),
        LLMRequest(task="name.suggest", messages=[LLMMessage(role="user", content="hi")], context={"count": 5}),
        LLMUsage(provider="fake", model=None, task="name.suggest", duration_ms=1, ok=True),
    ]


def test_models_round_trip_through_json(sample_facts):
    for model in _samples(sample_facts):
        dumped = model.model_dump(mode="json")
        json.dumps(dumped)  # plain JSON
        assert type(model).model_validate(dumped) == model, type(model).__name__


def test_agent_reply_actions_round_trip():
    from launch_agents.agents.base import AgentReply, TurnResult

    reply = AgentReply(
        messages=[ChatMessage(role=MessageRole.AGENT, agent=AgentId.WEBSITE, content="Building")],
        actions=[LockFacts(), ChooseName(name="Crumb", domain="crumb.io"), BuildWebsite(change_request="blue"),
                 OpenView(view="website")],
        hand_back=True,
    )
    again = AgentReply.model_validate(reply.model_dump(mode="json"))
    assert again == reply and isinstance(again.actions[1], ChooseName)
    turn = TurnResult(messages=reply.messages, facts=CaseFacts(), state=CaseState(), actions=reply.actions)
    assert TurnResult.model_validate_json(turn.model_dump_json()) == turn


def test_agent_message_requires_an_agent():
    with pytest.raises(ValidationError):
        ChatMessage(role=MessageRole.AGENT, content="who am I?")
    ok = ChatMessage(role=MessageRole.FOUNDER, founder_id="f1", content="hello")
    assert ok.agent is None and ok.kind == MessageKind.TEXT


def test_money_is_strings_and_timestamps_are_aware():
    assert GuideStep.model_fields["fee"].annotation == (str | None)
    assert names_match("Alice Chen", "alice chen")
    assert new_id("case").startswith("case_") and len(new_id("case")) == len("case_") + 12
    from launch_agents.domain import utcnow

    assert utcnow().tzinfo is not None


def test_errors_codes_and_statuses():
    expected = {
        "NotFoundError": ("not_found", 404), "InvalidStateError": ("invalid_state", 422),
        "FactsNotReadyError": ("facts_not_ready", 409), "NameNotChosenError": ("name_not_chosen", 409),
        "StaleVersionError": ("stale_version", 409), "NotASignerError": ("not_a_signer", 403),
        "AlreadySignedError": ("already_signed", 409), "DeployBlockedError": ("qa_failed_needs_override", 409),
        "LLMOutputError": ("llm_unavailable", 502), "ExternalServiceError": ("external_service", 502),
        "RetryableError": ("temporarily_unavailable", 503),
        "AuthRequiredError": ("auth_required", 401), "InvalidCredentialsError": ("invalid_credentials", 401),
        "ForbiddenError": ("forbidden", 403), "EmailNotVerifiedError": ("email_not_verified", 403),
        "CsrfError": ("csrf_failed", 403), "PlanRequiredError": ("plan_required", 402),
        "RateLimitedError": ("rate_limited", 429), "UsageLimitError": ("usage_limit", 429),
        "ConflictError": ("conflict", 409), "TokenInvalidError": ("token_invalid", 400),
        "NotExecutedError": ("not_executed", 409), "PaymentProviderError": ("payment_provider", 502),
        "WebhookSignatureError": ("webhook_invalid", 400),
    }
    for name, (code, status) in expected.items():
        cls = getattr(errors_module, name)
        assert issubclass(cls, LaunchError) and (cls.code, cls.http_status) == (code, status), name
    err = errors_module.NotFoundError("We couldn't find that company.", details={"case_id": "x"})
    assert err.message == "We couldn't find that company." and err.details == {"case_id": "x"}
    assert (RetryableJobError.code, RetryableJobError.http_status) == ("job_retry", 503)


# =========================================================================================
# 3. apply_patch, helpers, profiles, handoffs, zips, states, FakeLLM and the service fakes
# =========================================================================================
def test_apply_patch_none_leaves_values_and_lists_replace(sample_facts):
    same = apply_patch(sample_facts, FactsPatch())
    assert same == sample_facts and same is not sample_facts
    patched = apply_patch(sample_facts, FactsPatch(company_name="Crumb Ledger", name_preferences=["Crumb"],
                                                    website=WebsitePatch(pages=["Home", "Pricing"], about="We help")))
    assert patched.company_name == "Crumb Ledger" and patched.name_preferences == ["Crumb"]
    assert patched.website.pages == ["Home", "Pricing"] and patched.website.about == "We help"
    assert patched.website.services == [] and patched.state == "WY"
    assert sample_facts.company_name is None and sample_facts.website.pages == []  # pure


def test_apply_patch_matches_founders_by_id_then_email_then_name(sample_facts):
    by_id = apply_patch(sample_facts, FactsPatch(founders=[FounderPatch(id="f2", vesting_months=36)]))
    assert by_id.founders[1].vesting_months == 36 and len(by_id.founders) == 2
    by_email = apply_patch(sample_facts, FactsPatch(founders=[FounderPatch(email="BOB@example.com", name="Robert Diaz")]))
    assert [f.name for f in by_email.founders] == ["Alice Chen", "Robert Diaz"]
    by_name = apply_patch(sample_facts, FactsPatch(founders=[FounderPatch(name="alice chen", equity_percent=Decimal("55"))]))
    assert by_name.founders[0].equity_percent == Decimal("55") and by_name.founders[0].id == "f1"
    # id wins over email: f1 keeps its id even though the email belongs to f2
    both = apply_patch(sample_facts, FactsPatch(founders=[FounderPatch(id="f1", email="bob@example.com")]))
    assert both.founders[0].email == "bob@example.com" and both.founders[1].email == "bob@example.com"


def test_apply_patch_new_founders_get_fresh_ids_never_reused(sample_facts):
    added = apply_patch(sample_facts, FactsPatch(founders=[FounderPatch(name="Cara Lee")]))
    cara = added.founders[2]
    assert (cara.id, cara.email, cara.equity_percent, cara.vesting_months) == ("f3", "", Decimal(0), None)
    removed = apply_patch(added, FactsPatch(remove_founder_ids=["f2"], founders=[FounderPatch(name="Dan")]))
    assert [f.id for f in removed.founders] == ["f1", "f3", "f4"]
    again = apply_patch(removed, FactsPatch(remove_founder_ids=["f3"]))
    assert [f.id for f in apply_patch(again, FactsPatch(founders=[FounderPatch(name="Eve")])).founders] == ["f1", "f4", "f5"]
    nameless = apply_patch(sample_facts, FactsPatch(founders=[FounderPatch(email="who@example.com")]))
    assert len(nameless.founders) == 2


def test_apply_patch_c_corp_forces_delaware_and_state_is_upper_cased(sample_facts):
    corp = apply_patch(sample_facts, FactsPatch(entity_type=EntityType.C_CORP))
    assert corp.state == "DE" and corp.entity_type == EntityType.C_CORP
    assert apply_patch(CaseFacts(), FactsPatch(state=" wy ")).state == "WY"
    assert apply_patch(CaseFacts(), FactsPatch(state="ca", entity_type=EntityType.C_CORP)).state == "DE"


def test_date_and_text_helpers():
    assert deadline_83b(date(2026, 12, 1)) == date(2026, 12, 31)
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)
    assert add_months(date(2026, 12, 1), 12) == date(2027, 12, 1)
    assert add_months(date(2026, 3, 31), -1) == date(2026, 2, 28)
    assert days_until(date(2026, 12, 31), date(2026, 11, 23)) == 38
    assert days_until(date(2026, 12, 31), date(2027, 1, 2)) == -2
    assert slugify("Crumb & Co.") == "crumb-co"
    assert slugify("  Café Ünïcode!! ") == "cafe-unicode"
    assert domain_label("Crumb Ledger LLC") == "crumbledger"
    assert domain_label("Acme, Inc.") == "acme"
    assert domain_label("Bright Path Corporation") == "brightpath"
    assert domain_label("Co") == "co"


def test_agent_profiles_match_adr0009():
    rows = {
        "manager": ("Manager", "Manager", "llm", "briefcase", "agent-manager", False),
        "law": ("Law Agent", "Law", "llm", "scale", "agent-law", True),
        "name": ("Name Agent", "Names", "llm", "tag", "agent-name", True),
        "website": ("Website Agent", "Website", "llm", "globe", "agent-website", True),
        "qa": ("QA Agent", "QA", "llm", "shield-check", "agent-qa", False),
        "guide": ("Registration Guide Agent", "Guide", "llm", "list-checks", "agent-guide", True),
        "cap_table": ("Cap Table Builder", "Cap table", "deterministic", "pie-chart", "agent-cap-table", False),
        "signoff": ("Sign-off", "Sign-off", "deterministic", "pen-line", "agent-signoff", False),
    }
    assert [a.value for a in AGENT_PROFILES] == list(rows)
    for agent_id, profile in AGENT_PROFILES.items():
        assert profile.id == agent_id
        assert (profile.display_name, profile.short_name, profile.kind, profile.icon, profile.accent,
                profile.routable) == rows[agent_id.value]


def test_handoff_messages_have_fixed_wording():
    over = handoff_message(AgentId.MANAGER, AgentId.LAW, direction="handover", reason="legal question")
    assert over.content == "Manager brought in the Law Agent"
    assert (over.role, over.agent, over.kind) == (MessageRole.AGENT, AgentId.MANAGER, MessageKind.HANDOFF)
    assert over.payload == {"from": "manager", "to": "law", "direction": "handover", "reason": "legal question"}
    back = handoff_message(AgentId.LAW, AgentId.MANAGER, direction="return", reason="done")
    assert back.content == "Law Agent handed the conversation back to the Manager"
    assert back.agent == AgentId.LAW and back.payload["direction"] == "return"
    guide = handoff_message(AgentId.MANAGER, AgentId.GUIDE, direction="handover", reason="filing")
    assert guide.content == "Manager brought in the Registration Guide Agent"


def test_manager_greeting_uses_the_brand():
    from launch_agents.agents.manager import manager_greeting

    greeting = manager_greeting()
    assert greeting.agent == AgentId.MANAGER and greeting.kind == MessageKind.TEXT
    assert "the Manager at Charterly" in greeting.content
    assert [r.label for r in greeting.suggested_replies] == [
        "I want to start an LLC", "Help me choose LLC or C-Corp", "Find a company name"]
    assert "the Manager at Acme" in manager_greeting("Acme").content


def test_site_bundle_zip_is_deterministic_and_complete():
    bundle = SiteBundle(files=[
        SiteFile(path="index.html", content="<!doctype html><title>Ä</title>", content_type="text/html"),
        SiteFile(path="styles.css", content=":root{--color-text:#111}", content_type="text/css"),
    ])
    first, second = bundle.to_zip(), bundle.model_copy(deep=True).to_zip()
    assert first == second
    with zipfile.ZipFile(io.BytesIO(first)) as zf:
        assert zf.namelist() == ["index.html", "styles.css"]
        assert zf.read("index.html").decode("utf-8") == "<!doctype html><title>Ä</title>"
    assert bundle.get("styles.css").content_type == "text/css" and bundle.get("/index.html") is not None
    assert bundle.get("missing.html") is None


def test_us_states_curated():
    assert len(US_STATES) == 51 and "DC" in US_STATES
    for code, info in US_STATES.items():
        assert info.code == code and len(code) == 2 and info.name
        assert info.filing_office_url.startswith("https://") and info.name_search_url.startswith("https://")
    assert state_info("wy").name == "Wyoming"
    with pytest.raises(InvalidStateError):
        state_info("XX")


class _Answer(BaseModel):
    answer: str
    score: int


def _request(task: str = "demo.task", **context) -> LLMRequest:
    return LLMRequest(task=task, messages=[LLMMessage(role="user", content="hi")], context=context)


def test_fake_llm_resolution_order(monkeypatch):
    import launch_agents.agents.qa.fake as qa_fake

    monkeypatch.setitem(qa_fake.FAKE_HANDLERS, "demo.task", lambda r: "default")
    llm = FakeLLM()
    assert llm.complete(_request()) == "default"
    llm.register("demo.task", lambda r: f"handler:{r.context.get('n')}")
    assert llm.complete(_request(n=1)) == "handler:1"
    llm.script("demo.task", ["first", {"answer": "x", "score": 1}])
    assert llm.complete(_request()) == "first"
    assert llm.complete_json(_request(), _Answer) == _Answer(answer="x", score=1)
    assert llm.complete(_request(n=2)) == "handler:2"
    assert len(llm.calls) == 5 and llm.calls[0].task == "demo.task"
    assert FakeLLM(include_defaults=False, handlers={"x.y": lambda r: "ok"}).complete(_request("x.y")) == "ok"
    with pytest.raises(FakeLLMMissingHandler):
        FakeLLM(include_defaults=False).complete(_request("demo.task"))


def test_fake_llm_validates_json_like_a_real_provider():
    llm = FakeLLM(include_defaults=False)
    llm.register("demo.json", lambda r: {"answer": "yes", "score": "3"})
    assert llm.complete_json(_request("demo.json"), _Answer) == _Answer(answer="yes", score=3)
    llm.script("demo.json", ['{"answer": "s", "score": 2}', _Answer(answer="m", score=4), {"answer": "bad"}, "not json"])
    assert llm.complete_json(_request("demo.json"), _Answer).score == 2
    assert llm.complete_json(_request("demo.json"), _Answer).answer == "m"
    with pytest.raises(LLMOutputError):
        llm.complete_json(_request("demo.json"), _Answer)
    with pytest.raises(LLMOutputError):
        llm.complete_json(_request("demo.json"), _Answer)
    assert llm.complete(_request("demo.json")) == json.dumps({"answer": "yes", "score": "3"})


def test_agent_fake_modules_start_empty_and_are_loaded_lazily():
    from launch_agents.llm.fake import DEFAULT_HANDLER_MODULES

    assert DEFAULT_HANDLER_MODULES == tuple(
        f"launch_agents.agents.{a}.fake" for a in ("manager", "law", "name", "website", "qa", "guide"))
    for name in DEFAULT_HANDLER_MODULES:
        assert isinstance(importlib.import_module(name).FAKE_HANDLERS, dict)
    fake_source = (PACKAGE_DIR / "llm" / "fake.py").read_text(encoding="utf-8")
    assert "from ..agents" not in fake_source and "import launch_agents.agents" not in fake_source


def test_fake_domain_checker():
    checker = FakeDomainChecker(taken={"crumbledger.com"}, unknown={"crumbledger.co"})
    assert checker.check("CrumbLedger.com").status == DomainStatus.TAKEN
    unknown = checker.check("crumbledger.co")
    assert unknown.status == DomainStatus.UNKNOWN and unknown.detail
    available = checker.check("crumbledger.io")
    assert (available.status, available.source) == (DomainStatus.AVAILABLE, "fake")
    assert checker.calls == ["crumbledger.com", "crumbledger.co", "crumbledger.io"]
    assert FakeDomainChecker().check("acme.com").status == DomainStatus.TAKEN
    assert DEFAULT_FAKE_TAKEN == {"acme.com", "launch.com", "startup.com", "google.com", "apple.com"}


def test_fake_and_unconfigured_site_hosts():
    bundle = SiteBundle(files=[SiteFile(path="index.html", content="x", content_type="text/html")])
    host = FakeSiteHost()
    result = host.deploy("crumb-ledger-abc123", bundle)
    assert host.configured and (result.status, result.url, result.provider) == (
        "deployed", "https://crumb-ledger-abc123.fake-host.test", "fake")
    host.fail_next()
    assert host.deploy("crumb", bundle).status == "failed" and len(host.deploys) == 2
    none = UnconfiguredSiteHost().deploy("crumb", bundle)
    assert not UnconfiguredSiteHost.configured and none.status == "not_configured" and none.url is None
    assert none.message.startswith("Deploy isn't set up yet: add a NETLIFY_AUTH_TOKEN to publish.")


# =========================================================================================
# 4. document_sha256 and names_match
# =========================================================================================
def test_document_sha256_normalises_line_endings():
    import hashlib

    lf = "# IP Assignment\nAlice Chen\n"
    assert document_sha256(lf.replace("\n", "\r\n")) == document_sha256(lf)
    assert document_sha256(lf) == hashlib.sha256(lf.encode("utf-8")).hexdigest()
    assert document_sha256(lf) != document_sha256(lf + " ")


def test_names_match():
    assert names_match("alice  chen", "Alice Chen.")
    assert names_match(" Alice Chen ", "alice chen")
    assert names_match("Chen, Alice", "chen alice")
    assert not names_match("Alice", "Alice Chen")
    assert not names_match("", "")


# =========================================================================================
# 5. Settings: environments, LLM selection, per-agent models, production guards, redaction
# =========================================================================================
GOOD_PRODUCTION = {
    "APP_ENV": "production",
    "LLM_PROVIDER": "anthropic",
    "APP_BASE_URL": "https://app.example.com",
    "SECRET_KEY": "prod-secret-" + "x" * 32,
    "ANTHROPIC_API_KEY": "sk-ant-api-test-value",
    "STRIPE_SECRET_KEY": "sk_live_example_value",
    "STRIPE_WEBHOOK_SECRET": "whsec_example_value",
    "STRIPE_PRICE_LAUNCH_MONTHLY": "price_launch_m",
    "STRIPE_PRICE_LAUNCH_YEARLY": "price_launch_y",
    "STRIPE_PRICE_TEAM_MONTHLY": "price_team_m",
    "STRIPE_PRICE_TEAM_YEARLY": "price_team_y",
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PASSWORD": "smtp-password-value",
    "EMAIL_FROM": "hello@example.com",
    "LAUNCH_DB_URL": "postgresql+psycopg://app:pw@db:5432/app",
    "LAUNCH_CORS_ORIGINS": "https://app.example.com",
    "SUPPORT_EMAIL": "support@example.com",
}


def test_development_defaults():
    s = load_settings({})
    assert s.app_env == AppEnv.DEVELOPMENT and not s.is_production
    assert (s.email_provider, s.payments_provider, s.jobs_embedded_worker, s.log_format) == ("console", "fake", True, "text")
    assert (s.llm_provider, s.domain_checker, s.hosting_provider, s.fake_services) == ("fake", "rdap", "none", False)
    assert s.secret_key and len(s.secret_key) >= 32
    assert s.brand_name == "Charterly" and s.db_url == "sqlite:///./launch_agents.db"
    assert s.cors_origins == ["http://localhost:5173"] and s.app_base_url == "http://localhost:8000"
    assert load_settings({"STRIPE_SECRET_KEY": "sk_test_1"}).payments_provider == "stripe"
    assert load_settings({"NETLIFY_AUTH_TOKEN": "t"}).hosting_provider == "netlify"
    assert load_settings({"DATABASE_URL": "sqlite:///x.db"}).db_url == "sqlite:///x.db"
    assert load_settings({"LAUNCH_CORS_ORIGINS": "http://a.test, http://b.test/"}).cors_origins == ["http://a.test", "http://b.test"]
    assert load_settings({"LAUNCH_TODAY": "2026-11-23"}).today == date(2026, 11, 23)


def test_test_environment_defaults_to_every_fake():
    s = load_settings({"APP_ENV": "test"})
    assert s.fake_services and s.secret_key and len(s.secret_key) >= 32
    assert (s.llm_provider, s.domain_checker, s.hosting_provider, s.email_provider, s.payments_provider) == (
        "fake", "fake", "fake", "fake", "fake")
    assert s.jobs_embedded_worker and s.log_format == "text"
    assert load_settings({"APP_ENV": "test"}).secret_key == s.secret_key  # fixed test value
    explicit = load_settings({"APP_ENV": "test", "LLM_PROVIDER": "groq", "GROQ_API_KEY": "g"})
    assert explicit.llm_provider == "groq"  # an explicit choice wins when fakes are only the test default


def test_fake_services_force_fakes_but_explicit_hosting_wins():
    s = load_settings({"LAUNCH_FAKE_SERVICES": "1", "LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "k",
                       "EMAIL_PROVIDER": "smtp", "PAYMENTS_PROVIDER": "stripe", "DOMAIN_CHECKER": "rdap"})
    assert (s.llm_provider, s.email_provider, s.payments_provider, s.domain_checker, s.hosting_provider) == (
        "fake", "fake", "fake", "fake", "fake")
    assert load_settings({"LAUNCH_FAKE_SERVICES": "1", "HOSTING_PROVIDER": "none"}).hosting_provider == "none"


def test_production_defaults_and_a_correct_production_env_loads():
    s = load_settings(GOOD_PRODUCTION)
    assert s.is_production and s.llm_provider == "anthropic"
    assert (s.email_provider, s.payments_provider, s.jobs_embedded_worker, s.log_format) == ("smtp", "stripe", False, "json")
    no_yearly = {k: v for k, v in GOOD_PRODUCTION.items() if "YEARLY" not in k}
    with pytest.raises(ConfigError):
        load_settings(no_yearly)
    assert load_settings({**no_yearly, "BILLING_YEARLY_ENABLED": "false"}).billing_yearly_enabled is False


@pytest.mark.parametrize(
    "env, provider",
    [
        ({"ANTHROPIC_API_KEY": "a", "DEEPSEEK_API_KEY": "d", "GROQ_API_KEY": "g"}, "anthropic"),
        ({"DEEPSEEK_API_KEY": "d", "GROQ_API_KEY": "g"}, "deepseek"),
        ({"GROQ_API_KEY": "g"}, "groq"),
        ({}, "fake"),
        ({"CLAUDE_CODE_PATH": "/opt/claude"}, "fake"),  # claude_code is never chosen implicitly
        ({"LLM_PROVIDER": "claude_code"}, "claude_code"),
        ({"LLM_PROVIDER": "openai-compatible", "LLM_BASE_URL": "https://x.test", "LLM_API_KEY": "k"}, "openai-compatible"),
        ({"LAUNCH_FAKE_SERVICES": "1", "LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "a"}, "fake"),
    ],
)
def test_llm_selection_follows_adr0022(env, provider):
    assert load_settings(env).llm_provider == provider


def test_get_llm_constructs_the_selected_provider_without_calling_it():
    from launch_agents.llm.anthropic_provider import AnthropicProvider
    from launch_agents.llm.claude_code import ClaudeCodeProvider
    from launch_agents.llm.openai_compat import OpenAICompatibleProvider

    assert isinstance(get_llm(load_settings({})), FakeLLM)
    assert isinstance(get_llm(load_settings({"LLM_PROVIDER": "claude_code"})), ClaudeCodeProvider)
    assert isinstance(get_llm(load_settings({"ANTHROPIC_API_KEY": "a"})), AnthropicProvider)
    deepseek = get_llm(load_settings({"DEEPSEEK_API_KEY": "d"}))
    assert isinstance(deepseek, OpenAICompatibleProvider) and deepseek.preset == "deepseek"
    assert get_llm(load_settings({"GROQ_API_KEY": "g"})).preset == "groq"
    assert get_llm(load_settings({"LLM_PROVIDER": "openai-compatible"})).preset is None


def test_per_agent_models_and_efforts():
    s = load_settings({"ANTHROPIC_API_KEY": "a", "LLM_MODEL": "claude-opus-5-5", "LLM_MODEL_QA": "claude-haiku-5-5",
                       "LLM_MODEL_NAME": "claude-haiku-5-5", "LLM_EFFORT": "high", "LLM_EFFORT_QA": "low"})
    assert s.llm_models == {"qa": "claude-haiku-5-5", "name": "claude-haiku-5-5"}
    assert s.model_for("qa.review") == "claude-haiku-5-5" and s.model_for("name.suggest") == "claude-haiku-5-5"
    assert s.model_for("law.answer") == "claude-opus-5-5"
    assert load_settings({}).model_for("law.answer") is None
    assert (s.effort_for("qa.review"), s.effort_for("manager.route")) == ("low", "high")


def test_production_guards_list_every_problem_in_one_error():
    bad = {
        **GOOD_PRODUCTION,
        "LLM_PROVIDER": "claude_code",
        "PAYMENTS_PROVIDER": "fake",
        "EMAIL_PROVIDER": "console",
        "LAUNCH_DB_URL": "sqlite:///./prod.db",
        "SECRET_KEY": "short",
        "APP_BASE_URL": "http://app.example.com",
        "DEMO_MODE": "1",
        "STRIPE_PRICE_TEAM_MONTHLY": "",
        "SUPPORT_EMAIL": "",
        "PLAN_LAUNCH_PRICE_MONTH_CENTS": "0",
    }
    with pytest.raises(ConfigError) as caught:
        load_settings(bad)
    problems = caught.value.problems
    text = "\n".join(problems)
    for needle in ("claude_code", "PAYMENTS_PROVIDER", "EMAIL_PROVIDER", "PostgreSQL", "SECRET_KEY", "APP_BASE_URL",
                   "DEMO_MODE", "STRIPE_PRICE_TEAM_MONTHLY", "SUPPORT_EMAIL", "PLAN_LAUNCH_PRICE_MONTH_CENTS"):
        assert needle in text, needle
    assert len(problems) == 10
    assert str(caught.value).count("\n- ") == len(problems)


def test_more_production_guards():
    def problems(**overrides):
        with pytest.raises(ConfigError) as caught:
            load_settings({**GOOD_PRODUCTION, **overrides})
        return "\n".join(caught.value.problems)

    assert "LLM_PROVIDER=fake" in problems(LLM_PROVIDER="fake")
    assert "ANTHROPIC_API_KEY" in problems(ANTHROPIC_API_KEY="")
    assert "LAUNCH_FAKE_SERVICES" in problems(LAUNCH_FAKE_SERVICES="1")
    assert "EMAIL_DROP_FILE" in problems(EMAIL_DROP_FILE="/tmp/mail.jsonl")
    assert "STRIPE_WEBHOOK_SECRET" in problems(STRIPE_WEBHOOK_SECRET="")
    assert "SMTP_HOST" in problems(SMTP_HOST="")
    assert "LAUNCH_CORS_ORIGINS" in problems(LAUNCH_CORS_ORIGINS="*")
    assert "Free plan" in problems(PLAN_FREE_PRICE_MONTH_CENTS="100")
    with pytest.raises(ConfigError):
        load_settings({"PLAN_TEAM_MAX_COMPANIES": "-1"})  # negative numbers are refused everywhere
    with pytest.raises(ConfigError):
        load_settings({"LLM_PROVIDER": "bogus"})
    with pytest.raises(ConfigError):
        load_settings({"SMTP_PORT": "abc"})
    with pytest.raises(ConfigError):
        load_settings({"APP_ENV": "staging"})


def test_secrets_never_appear_in_repr():
    secrets = {
        "SECRET_KEY": "secret-key-value-1234567890-abcdef",
        "ANTHROPIC_API_KEY": "anthropic-key-value", "DEEPSEEK_API_KEY": "deepseek-key-value",
        "GROQ_API_KEY": "groq-key-value", "LLM_API_KEY": "llm-key-value", "NETLIFY_AUTH_TOKEN": "netlify-token-value",
        "SMTP_PASSWORD": "smtp-password-value", "STRIPE_SECRET_KEY": "stripe-secret-value",
        "STRIPE_WEBHOOK_SECRET": "webhook-secret-value",
    }
    urls = {
        "LAUNCH_DB_URL": "postgresql+psycopg://app:S3cretPw@db/launch",
        "LLM_BASE_URL": "https://llm-user:Llm/Pa@ss@llm.example.com:8443/v1?x=1",
    }
    s = load_settings({**secrets, **urls})
    for text in (repr(s), str(s)):
        for value in [*secrets.values(), "S3cretPw", "Llm/Pa", "Pa@ss"]:
            assert value not in text
        assert "postgresql+psycopg://app:***@db/launch" in text
        assert "https://llm-user:***@llm.example.com:8443/v1?x=1" in text
    assert "secret_key='***'" in repr(s) and "app_env=" in repr(s)
    for db_url in ("postgresql+psycopg://app:pa?ss@db/launch", "postgresql+psycopg://app:pa#ss@db/launch"):
        masked = load_settings({"LAUNCH_DB_URL": db_url})  # round-2 finding: '?' / '#' in the password
        for text in (repr(masked), str(masked)):
            assert "pa?ss" not in text and "pa#ss" not in text
            assert "db_url='postgresql+psycopg://app:***@db/launch'" in text
    assert s.anthropic_api_key == "anthropic-key-value"  # still usable by code
    assert s.db_url == urls["LAUNCH_DB_URL"] and s.llm_base_url == urls["LLM_BASE_URL"]
    plain = load_settings({"LAUNCH_DB_URL": "sqlite:///./x.db", "LLM_BASE_URL": "https://user@llm.example.com/v1"})
    assert "db_url='sqlite:///./x.db'" in repr(plain)  # nothing to mask
    assert "llm_base_url='https://user@llm.example.com/v1'" in repr(plain)
    port_only = load_settings({"LLM_BASE_URL": "https://user@llm.example.com:8443/v1?mode=fast"})
    assert "llm_base_url='https://user@llm.example.com:8443/v1?mode=fast'" in repr(port_only)


@pytest.mark.parametrize("password", [
    "pa?ss", "pa#ss", "p?a#s", "pa:ss", "pa/ss", "pa@ss", "?lead", "#lead", "trail?", "trail#",
    "x?y=1&z#w@v", "S3cret!$*()[]{};,'~",
])
def test_db_url_password_never_appears_in_repr(password):
    """Whatever characters the password holds, SQLAlchemy (which consumes ``db_url``) parses it
    as the password and connects with it, so ``repr``/``str`` must never show it (AC 5, ADR-0021)."""
    from sqlalchemy.engine import make_url

    url = f"postgresql+psycopg://app:{password}@db:5432/launch?sslmode=require"
    if "@" not in password:  # a real credential: SQLAlchemy connects with exactly this password
        assert make_url(url).password == password and make_url(url).host == "db"
    else:  # SQLAlchemy splits at the first "@"; the whole value must still be hidden
        assert password.startswith(make_url(url).password)
    s = load_settings({"LAUNCH_DB_URL": url, "LLM_BASE_URL": f"https://llm-user:{password}@llm.example.com/v1"})
    for text in (repr(s), str(s)):
        assert password not in text
        assert "postgresql+psycopg://app:***@db:5432/launch?sslmode=require" in text
        assert "https://llm-user:***@llm.example.com/v1" in text
    assert s.db_url == url  # the real value is still usable by code


def test_db_url_query_password_never_appears_in_repr():
    """psycopg also takes the password as a query parameter; secret-named parameters are masked."""
    url = "postgresql+psycopg://app@db/launch?sslmode=require&password=Qw?e#rt%26y&application_name=launch"
    s = load_settings({"LAUNCH_DB_URL": url, "LLM_BASE_URL": "https://llm.example.com/v1?API_KEY=k3y-value"})
    for text in (repr(s), str(s)):
        assert "Qw?e#rt" not in text and "k3y-value" not in text
        assert "postgresql+psycopg://app@db/launch?sslmode=require&password=***&application_name=launch" in text
        assert "https://llm.example.com/v1?API_KEY=***" in text


def test_settings_are_frozen():
    s = load_settings({})
    with pytest.raises(ValidationError):
        s.app_base_url = "https://x"  # type: ignore[misc]
    assert s.model_copy(update={"demo_mode": True}).demo_mode is True


# =========================================================================================
# 6. Request context, actors and case access
# =========================================================================================
def _user() -> User:
    return User(id="usr_alice", email="alice@example.com", full_name="Alice Chen", created_at=NOW)


def test_request_context_require_user():
    from launch_agents.domain import AuthRequiredError

    with pytest.raises(AuthRequiredError):
        RequestContext(request_id="r1", user=None).require_user()
    assert RequestContext(request_id="r1", user=_user()).require_user().id == "usr_alice"
    system = RequestContext.system()
    assert (system.request_id, system.user, system.demo_mode) == ("system", None, False)
    assert not _user().email_verified and _user().model_copy(update={"email_verified_at": NOW}).email_verified


def test_case_access_permissions_features_and_system():
    from launch_agents.access import ROLE_PERMISSIONS
    from launch_agents.domain import ForbiddenError

    actor = Actor(kind="user", user_id="usr_bob", founder_id="f2", ip="1.2.3.4", user_agent="ua", request_id="r1")
    member = CaseAccess(case_id="case_1", actor=actor,
                        membership=Membership(case_id="case_1", user_id="usr_bob", role=MemberRole.MEMBER,
                                              founder_id="f2", joined_at=NOW),
                        permissions=ROLE_PERMISSIONS[MemberRole.MEMBER], entitlements=Entitlements.for_plan(PlanId.FREE),
                        billing_user_id="usr_alice")
    member.require(Permission.CHAT)
    with pytest.raises(ForbiddenError):
        member.require(Permission.MANAGE_TEAM)
    with pytest.raises(PlanRequiredError) as caught:
        member.require_feature(Feature.ESIGN)
    assert caught.value.details == {"feature": "esign", "required_plan": "launch"}
    assert caught.value.message == "Electronic signatures are included in the Launch and Team plans."
    assert member.founder_id == "f2"
    system = CaseAccess.system("case_1", Entitlements.for_plan(PlanId.LAUNCH), billing_user_id="usr_alice")
    assert system.permissions == frozenset(Permission) and system.membership is None
    assert system.actor.audit_actor == "system" and system.actor.kind == "system" and system.founder_id is None
    for permission in Permission:
        system.require(permission)
    system.require_feature(Feature.ESIGN)
    assert ROLE_PERMISSIONS[MemberRole.OWNER] == frozenset(Permission)
    assert ROLE_PERMISSIONS[MemberRole.MEMBER] == frozenset(Permission) - {Permission.MANAGE_TEAM, Permission.DELETE_COMPANY}


def test_actor_audit_actor_prefers_founder_then_user():
    base = dict(ip=None, user_agent=None, request_id="r")
    assert Actor(kind="user", user_id="usr_1", founder_id="f1", **base).audit_actor == "f1"
    assert Actor(kind="user", user_id="usr_1", founder_id=None, **base).audit_actor == "usr_1"
    assert Actor(kind="system", user_id=None, founder_id=None, **base).audit_actor == "system"


def test_plan_required_messages_per_feature():
    from launch_agents.domain import feature_required_message

    assert feature_required_message(Feature.WEBSITE_DEPLOY) == "Publishing your website is included in the Launch and Team plans."
    assert feature_required_message(Feature.DOCUMENTS) == "Drafting founding documents is included in the Launch and Team plans."


# =========================================================================================
# 7. Plans and entitlements (ADR-0038)
# =========================================================================================
def test_default_plans_match_the_adr0038_table():
    expected = {
        PlanId.FREE: (0, 0, 0, 1, 300, SupportLevel.BASIC, "Help guides and email, best effort", False, []),
        PlanId.LAUNCH: (1, 2900, 29000, 3, 2000, SupportLevel.STANDARD, "Email, reply within 2 business days", True,
                        list(Feature)),
        PlanId.TEAM: (2, 7900, 79000, 15, 10000, SupportLevel.PRIORITY,
                      "Priority email, reply within 1 business day, answered first", True, list(Feature)),
    }
    assert list(PLANS) == [PlanId.FREE, PlanId.LAUNCH, PlanId.TEAM]
    for plan_id, (rank, month, year, companies, ai, support, label, yearly, features) in expected.items():
        plan = PLANS[plan_id]
        assert plan.id == plan_id and plan.name == plan_id.value.capitalize()
        assert (plan.rank, plan.price_month_cents, plan.price_year_cents, plan.max_companies,
                plan.llm_calls_per_month) == (rank, month, year, companies, ai)
        assert plan.price_year_cents == 10 * plan.price_month_cents
        assert (plan.support, plan.support_label, plan.yearly_available, plan.features) == (support, label, yearly, features)
        assert plan.tagline and plan.highlights and label in plan.highlights
        ent = Entitlements.for_plan(plan_id)
        assert (ent.plan, ent.features, ent.max_companies, ent.llm_calls_per_month, ent.support) == (
            plan_id, frozenset(features), companies, ai, support)
        assert ent.has(Feature.ESIGN) is (plan_id != PlanId.FREE)
    assert "300 AI messages a month" in PLANS[PlanId.FREE].highlights
    assert "Up to 15 companies" in PLANS[PlanId.TEAM].highlights and "1 company" in PLANS[PlanId.FREE].highlights
    assert DEFAULT_PLAN_AMOUNTS[PlanId.TEAM].ai_messages_per_month == 10000


def test_plan_amount_override_changes_only_that_number():
    plans = load_settings({"PLAN_TEAM_AI_MESSAGES": "20000"}).plans()
    assert plans[PlanId.FREE] == PLANS[PlanId.FREE] and plans[PlanId.LAUNCH] == PLANS[PlanId.LAUNCH]
    team, default = plans[PlanId.TEAM], PLANS[PlanId.TEAM]
    assert team.llm_calls_per_month == 20000
    assert "20,000 AI messages a month" in team.highlights and "10,000 AI messages a month" not in team.highlights
    changed = {k for k in type(team).model_fields if getattr(team, k) != getattr(default, k)}
    assert changed == {"llm_calls_per_month", "highlights"}
    assert [h for h in team.highlights if "AI messages" not in h] == [h for h in default.highlights if "AI messages" not in h]
    assert Entitlements.for_plan(PlanId.TEAM, plans).llm_calls_per_month == 20000


def test_yearly_can_be_disabled_everywhere():
    plans = load_settings({"BILLING_YEARLY_ENABLED": "false"}).plans()
    assert all(not p.yearly_available for p in plans.values())
    assert load_settings({}).plans() == dict(PLANS)


def test_plan_navigation_helpers():
    assert lowest_plan_with(Feature.ESIGN).id == PlanId.LAUNCH
    assert lowest_plan_with(Feature.WEBSITE_DEPLOY).id == PlanId.LAUNCH
    assert next_plan_for_companies(PlanId.FREE).id == PlanId.LAUNCH
    assert next_plan_for_companies(PlanId.LAUNCH).id == PlanId.TEAM
    assert next_plan_for_companies(PlanId.TEAM) is None


def test_static_entitlements_return_the_configured_plan():
    assert StaticEntitlements(PlanId.TEAM).for_user("usr_1").plan == PlanId.TEAM
    assert StaticEntitlements(PlanId.FREE).for_user("usr_1") == Entitlements.for_plan(PlanId.FREE)
    assert StaticEntitlements().for_user(None).plan == PlanId.LAUNCH


# =========================================================================================
# 8. InlineJobRunner
# =========================================================================================
def test_inline_runner_runs_the_handler_at_once():
    runner = InlineJobRunner()
    seen = []
    runner.registry.register("demo.echo", lambda job, ctx: seen.append((job.payload, ctx.attempt)) or {"echo": job.payload["x"]})
    job = runner.enqueue("demo.echo", {"x": 1}, case_id="case_1", user_id="usr_1")
    assert (job.status, job.result, job.attempts, job.error) == (JobStatus.SUCCEEDED, {"echo": 1}, 1, None)
    assert job.finished_at is not None and seen == [({"x": 1}, 1)]
    assert runner.get(job.id) == job and runner.list_for_case("case_1") == [job]


def test_inline_runner_retries_retryable_errors():
    runner = InlineJobRunner()
    calls = {"n": 0}

    def flaky(job, ctx):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RetryableJobError("The registry is busy.")
        return {"ok": True}

    runner.register("demo.flaky", flaky)
    job = runner.enqueue("demo.flaky", {})
    assert (job.status, job.attempts, job.result) == (JobStatus.SUCCEEDED, 3, {"ok": True})

    def always(job, ctx):
        raise RetryableJobError("still busy")

    runner.register("demo.always", always)
    exhausted = runner.enqueue("demo.always", {}, max_attempts=2)
    assert (exhausted.status, exhausted.attempts) == (JobStatus.FAILED, 2) and exhausted.error


def test_inline_runner_fails_plain_exceptions_with_a_friendly_error():
    from launch_agents.ports.jobs import GENERIC_JOB_ERROR

    runner = InlineJobRunner()
    runner.register("demo.boom", lambda job, ctx: 1 / 0)
    job = runner.enqueue("demo.boom", {}, max_attempts=5)
    assert (job.status, job.attempts, job.error) == (JobStatus.FAILED, 1, GENERIC_JOB_ERROR)
    assert "ZeroDivision" not in job.error
    runner.register("demo.llm", lambda job, ctx: (_ for _ in ()).throw(LLMOutputError("The AI is unavailable.")))
    assert runner.enqueue("demo.llm", {}).error == "The AI is unavailable."


def test_inline_runner_dedupe_unknown_kind_and_retry():
    from launch_agents.domain import NotFoundError
    from launch_agents.ports.jobs import UNKNOWN_JOB_KIND_ERROR

    runner = InlineJobRunner()
    count = {"n": 0}
    runner.register("demo.once", lambda job, ctx: count.update(n=count["n"] + 1) or {"n": count["n"]})
    first = runner.enqueue("demo.once", {}, dedupe_key="once:1")
    second = runner.enqueue("demo.once", {"other": True}, dedupe_key="once:1")
    assert first.id == second.id and count["n"] == 1
    unknown = runner.enqueue("demo.nobody", {})
    assert (unknown.status, unknown.error, unknown.attempts) == (JobStatus.FAILED, UNKNOWN_JOB_KIND_ERROR, 0)
    with pytest.raises(NotFoundError):
        runner.get("job_missing")
    with pytest.raises(InvalidStateError):
        runner.retry(first.id)
    runner.register("demo.nobody", lambda job, ctx: {"late": True})
    retried = runner.retry(unknown.id)
    assert (retried.status, retried.attempts, retried.result) == (JobStatus.SUCCEEDED, 1, {"late": True})


def test_job_registry_raises_key_error_for_unknown_kinds():
    from launch_agents.ports import JobRegistry

    registry = JobRegistry()
    with pytest.raises(KeyError):
        registry.handler("x")
    registry.register("x", lambda job, ctx: None)
    assert "x" in registry and registry.kinds() == ["x"]


# =========================================================================================
# 9. Mailer, email sender and payment gateway fakes
# =========================================================================================
def test_recording_mailer_records_and_deduplicates():
    mailer = RecordingMailer()
    first = mailer.send(EmailTemplate.SIGNATURE_NEEDED, "bob@example.com", {"document_title": "IP"},
                        case_id="case_1", dedupe_key="sig:doc_1:1:f2")
    again = mailer.send(EmailTemplate.SIGNATURE_NEEDED, "bob@example.com", {"document_title": "IP"},
                        dedupe_key="sig:doc_1:1:f2")
    other = mailer.send(EmailTemplate.VERIFY_EMAIL, "alice@example.com", {"link": "x"})
    assert first and other and again is None and len(mailer.sent) == 2
    template, to, data, key = mailer.sent[0]
    assert (template, to, data, key) == (EmailTemplate.SIGNATURE_NEEDED, "bob@example.com", {"document_title": "IP"},
                                         "sig:doc_1:1:f2")
    assert mailer.meta[0]["case_id"] == "case_1" and len(mailer.to("ALICE@example.com")) == 1


def test_fake_email_sender_fail_next():
    sender = FakeEmailSender()
    message = EmailMessage(to="a@x.test", subject="s", text="t", html="h", template=EmailTemplate.PASSWORD_RESET)
    sender.fail_next(2)
    sender.fail_next(1, transient=False)
    results = [sender.send(message) for _ in range(4)]
    assert [(r.ok, r.transient) for r in results] == [(False, True), (False, True), (False, False), (True, False)]
    assert sender.sent == [message] and results[3].provider_id


def test_recording_notifier():
    notifier = RecordingNotifier()
    doc = _samples_document()
    notifier.signatures_needed("case_1", doc, ["f1", "f2"])
    notifier.document_executed("case_1", doc)
    assert [(e.kind, e.founder_ids) for e in notifier.events] == [("signatures_needed", ("f1", "f2")),
                                                                  ("document_executed", ())]


def _samples_document() -> Document:
    return Document(id="doc_1", case_id="case_1", kind=DocumentKind.IP_ASSIGNMENT, title="IP", founder_id=None,
                    version=1, content="x", status=DocumentStatus.AWAITING_SIGNATURES, required_signers=["f1"],
                    signatures=[], created_at=NOW, updated_at=NOW)


def test_fake_payment_gateway_checkout_and_webhooks(settings):
    from launch_agents.domain import WebhookSignatureError
    from launch_agents.ports import fake_price_id

    gw = FakePaymentGateway(settings, clock=lambda: NOW)
    assert (gw.name, gw.live) == ("fake", False)
    customer = gw.create_customer(email="alice@example.com", user_id="usr_alice")
    session = gw.create_checkout_session(customer_id=customer, price_id=fake_price_id(PlanId.LAUNCH, BillingInterval.MONTH),
                                         user_id="usr_alice", success_url="s", cancel_url="c")
    assert session.url == f"{settings.app_base_url}/app/billing/test-checkout?session={session.id}"
    completed = gw.complete_checkout(session.id)
    assert (completed.type, completed.client_reference_id, completed.status, completed.customer_id) == (
        "checkout.session.completed", "usr_alice", SubscriptionStatus.ACTIVE, customer)
    assert completed.current_period_end == NOW + timedelta(days=30)
    payload, header = gw.delivered[-1]
    assert gw.parse_webhook(payload, header) == completed
    team_price = fake_price_id(PlanId.TEAM, BillingInterval.YEAR)
    changed = gw.change_subscription_price(subscription_id=completed.subscription_id, price_id=team_price)
    assert changed.type == "customer.subscription.updated" and changed.price_id == team_price
    assert gw.parse_webhook(*gw.delivered[-1]) == changed
    cancelled = gw.cancel(customer)
    assert (cancelled.type, cancelled.status) == ("customer.subscription.deleted", SubscriptionStatus.CANCELED)
    assert gw.parse_webhook(*gw.delivered[-1]) == cancelled
    assert len(gw.delivered) == 3
    tampered = payload.replace(b"usr_alice", b"usr_mallory")
    with pytest.raises(WebhookSignatureError):
        gw.parse_webhook(tampered, header)
    with pytest.raises(WebhookSignatureError):
        gw.parse_webhook(payload, None)
    with pytest.raises(WebhookSignatureError):
        FakePaymentGateway(settings.model_copy(update={"stripe_webhook_secret": "whsec_other"})).parse_webhook(payload, header)
    for bad_header in ("t=été,v1=abc", "t=1,v1=é"):  # non-ASCII is a bad signature, not a crash
        with pytest.raises(WebhookSignatureError):
            gw.parse_webhook(payload, bad_header)
    assert gw.create_portal_session(customer_id=customer, return_url="http://testserver/app/settings/billing").startswith(
        "http://testserver/app/settings/billing?portal=fake")


def test_fake_payment_gateway_price_amounts_follow_the_settings():
    from launch_agents.ports import fake_price_id

    s = load_settings({**_test_env(), "PLAN_LAUNCH_PRICE_MONTH_CENTS": "3100", "STRIPE_PRICE_TEAM_MONTHLY": "price_team_m"})
    gw = FakePaymentGateway(s)
    assert gw.price_amount(fake_price_id(PlanId.LAUNCH, BillingInterval.MONTH)) == (3100, BillingInterval.MONTH)
    assert gw.price_amount(fake_price_id(PlanId.TEAM, BillingInterval.YEAR)) == (79000, BillingInterval.YEAR)
    assert gw.price_amount("price_team_m") == (7900, BillingInterval.MONTH)
    assert gw.price_amount("price_unknown") is None
    with pytest.raises(InvalidStateError):
        gw.complete_checkout("cs_missing")


# =========================================================================================
# 10. call_with_retry and Deadline
# =========================================================================================
def test_call_with_retry_retries_only_transient_errors():
    import httpx

    sleeps: list[float] = []
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise httpx.ConnectError("down")
        return "ok"

    retried: list[int] = []
    policy = RetryPolicy(attempts=3, base_delay_s=0.5, max_delay_s=8, jitter=False)
    assert call_with_retry(flaky, policy, sleep=sleeps.append, on_retry=lambda n, e: retried.append(n)) == "ok"
    assert sleeps == [0.5, 1.0] and retried == [1, 2]

    def permanent():
        attempts["n"] += 1
        raise ValueError("bad input")

    attempts["n"] = 0
    with pytest.raises(ValueError):
        call_with_retry(permanent, policy, sleep=sleeps.append)
    assert attempts["n"] == 1

    def always():
        attempts["n"] += 1
        raise RetryableError("busy")

    attempts["n"], sleeps[:] = 0, []
    with pytest.raises(RetryableError):
        call_with_retry(always, RetryPolicy(attempts=4, base_delay_s=1, max_delay_s=3, jitter=False), sleep=sleeps.append)
    assert attempts["n"] == 4 and sleeps == [1, 2, 3]


def test_retry_after_and_jitter():
    import httpx

    request = httpx.Request("GET", "https://x.test")
    limited = httpx.HTTPStatusError("429", request=request,
                                    response=httpx.Response(429, headers={"Retry-After": "2"}, request=request))
    sleeps: list[float] = []
    calls = {"n": 0}

    def once_limited():
        calls["n"] += 1
        if calls["n"] == 1:
            raise limited
        return 1

    assert call_with_retry(once_limited, RetryPolicy(jitter=False), sleep=sleeps.append) == 1 and sleeps == [2.0]
    from launch_agents.reliability import retry_delay

    delays = {round(retry_delay(RetryPolicy(base_delay_s=1.0), 1), 3) for _ in range(50)}
    assert all(0.8 <= d <= 1.2 for d in delays) and len(delays) > 1


def test_is_transient():
    import httpx

    request = httpx.Request("GET", "https://x.test")

    def status(code):
        return httpx.HTTPStatusError(str(code), request=request, response=httpx.Response(code, request=request))

    assert all(is_transient(status(c)) for c in (408, 425, 429, 500, 502, 503, 504))
    assert not any(is_transient(status(c)) for c in (400, 401, 403, 404, 422))
    assert is_transient(httpx.ReadTimeout("slow")) and is_transient(httpx.ConnectError("down"))
    assert is_transient(RetryableError("x")) and is_transient(TimeoutError())
    assert not is_transient(errors_module.ExternalServiceError("x")) and not is_transient(ValueError())


def test_deadline_expires():
    now = {"t": 100.0}
    deadline = Deadline(12, clock=lambda: now["t"])
    assert deadline.remaining() == 12 and not deadline.expired()
    now["t"] = 107.5
    assert deadline.remaining() == pytest.approx(4.5)
    now["t"] = 113
    assert deadline.remaining() == 0 and deadline.expired()


# =========================================================================================
# 11. Usage reporting
# =========================================================================================
def test_usage_sink_collects_inside_its_block_and_nests():
    usage = LLMUsage(provider="x", model=None, task="t.a", duration_ms=1, ok=True)
    outer: list[LLMUsage] = []
    inner: list[LLMUsage] = []
    report_usage(usage)  # outside any sink: dropped
    with usage_sink(outer.append):
        report_usage(usage)
        with usage_sink(inner.append):
            report_usage(usage.model_copy(update={"task": "t.b"}))
        report_usage(usage.model_copy(update={"task": "t.c"}))
    report_usage(usage)
    assert [u.task for u in outer] == ["t.a", "t.b", "t.c"] and [u.task for u in inner] == ["t.b"]


def test_fake_llm_reports_one_usage_per_call():
    llm = FakeLLM(include_defaults=False, handlers={"demo.task": lambda r: "hi"})
    llm.script("demo.bad", ["{}"])
    seen: list[LLMUsage] = []
    with usage_sink(seen.append):
        llm.complete(_request())
        llm.complete(_request())
        with pytest.raises(LLMOutputError):
            llm.complete_json(_request("demo.bad"), _Answer)
    assert [(u.provider, u.task, u.ok, u.input_tokens, u.output_tokens) for u in seen] == [
        ("fake", "demo.task", True, None, None), ("fake", "demo.task", True, None, None),
        ("fake", "demo.bad", False, None, None)]


# =========================================================================================
# 12. Schema: migration 0001 == tables.py == ADR-0027
# =========================================================================================
_ADR0012 = {
    "messages": "id case_id seq role agent founder_id kind content payload_json suggested_json created_at",
    "documents": "id case_id kind founder_id title version content status required_signers_json created_at updated_at",
    "document_versions": "document_id version content created_by created_at",
    "audit_log": "id case_id document_id actor action from_version to_version detail_json at",
    "checklist_items": "case_id item_id done updated_by updated_at",
    "site_builds": "id case_id version content_json files_json qa_reports_json qa_passed fix_rounds status deploy_url "
                   "deploy_message override_by created_at updated_at",
}
EXPECTED_COLUMNS = {
    "users": "id email full_name password_hash email_verified_at is_admin created_at updated_at",
    "sessions": "token_hash user_id created_at last_seen_at expires_at revoked_at ip user_agent",
    "auth_tokens": "token_hash user_id purpose created_at expires_at used_at",
    "cases": "id created_at updated_at facts_json state_json created_by billing_user_id",
    "memberships": "case_id user_id role founder_id joined_at",
    "invites": "id case_id email founder_id token_hash invited_by created_at expires_at accepted_at revoked_at",
    "signatures": "document_id founder_id version signed_at user_id typed_name consent_version ip user_agent "
                  "content_sha256 acted_by_user_id",
    "subscriptions": "user_id plan interval status current_period_end cancel_at_period_end provider_customer_id "
                     "provider_subscription_id updated_at",
    "billing_events": "id type received_at processed_at error payload_json",
    "jobs": "id kind status case_id user_id payload_json result_json error attempts max_attempts run_at locked_by "
            "locked_until dedupe_key created_at updated_at finished_at",
    "worker_heartbeats": "worker_id last_seen_at",
    "email_outbox": "id to_email template subject text_body html_body status attempts user_id case_id dedupe_key "
                    "provider_id error created_at sent_at",
    "llm_usage": "id user_id case_id task provider model input_tokens output_tokens duration_ms ok at",
    "rate_limits": "key window_start count",
    "admin_audit": "id admin_user_id action target detail_json at",
    **_ADR0012,
}
EXPECTED_KEYS = {
    "users": ("id",), "sessions": ("token_hash",), "auth_tokens": ("token_hash",), "cases": ("id",),
    "memberships": ("case_id", "user_id"), "invites": ("id",), "messages": ("id",), "documents": ("id",),
    "document_versions": ("document_id", "version"), "signatures": ("document_id", "founder_id", "version"),
    "audit_log": ("id",), "checklist_items": ("case_id", "item_id"), "site_builds": ("id",),
    "subscriptions": ("user_id",), "billing_events": ("id",), "jobs": ("id",), "worker_heartbeats": ("worker_id",),
    "email_outbox": ("id",), "llm_usage": ("id",), "rate_limits": ("key", "window_start"), "admin_audit": ("id",),
}
EXPECTED_UNIQUE = {
    ("users", ("email",)), ("memberships", ("case_id", "founder_id")), ("invites", ("token_hash",)),
    ("messages", ("case_id", "seq")), ("documents", ("case_id", "kind", "founder_id")),
    ("site_builds", ("case_id", "version")), ("subscriptions", ("provider_customer_id",)),
    ("jobs", ("dedupe_key",)), ("email_outbox", ("dedupe_key",)),
}


def test_tables_match_adr0027():
    from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint

    from launch_agents.persistence.tables import NAMING_CONVENTION, TABLE_NAMES, metadata

    assert set(TABLE_NAMES) == set(EXPECTED_COLUMNS) and len(TABLE_NAMES) == 21
    assert metadata.naming_convention == {**metadata.naming_convention, **NAMING_CONVENTION}
    uniques = set()
    for name, table in metadata.tables.items():
        assert [c.name for c in table.columns] == EXPECTED_COLUMNS[name].split(), name
        assert tuple(c.name for c in table.primary_key.columns) == EXPECTED_KEYS[name], name
        for column in table.columns:
            assert isinstance(column.type, (String, Text, Integer, Boolean, DateTime)), (name, column.name)
            if isinstance(column.type, DateTime):
                assert column.type.timezone, (name, column.name)
        uniques |= {(name, tuple(c.name for c in con.columns)) for con in table.constraints
                    if isinstance(con, UniqueConstraint)}
    assert uniques == EXPECTED_UNIQUE
    fks = {(t.name, fk.parent.name): (fk.column.table.name, fk.ondelete)
           for t in metadata.tables.values() for fk in t.foreign_keys}
    assert fks[("messages", "case_id")] == ("cases", "CASCADE")
    assert fks[("signatures", "document_id")] == ("documents", "CASCADE")
    assert fks[("signatures", "user_id")] == ("users", "SET NULL")
    assert fks[("cases", "billing_user_id")] == ("users", "SET NULL")
    assert fks[("memberships", "case_id")] == ("cases", "CASCADE")
    assert ("audit_log", "document_id") not in fks  # audit outlives deleted documents


def test_alembic_upgrade_head_creates_exactly_the_schema(tmp_path):
    pytest.importorskip("alembic", reason="package alembic not installed (ADR-0025)")
    from alembic import command
    from alembic.autogenerate import compare_metadata
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine, inspect

    from launch_agents.persistence.tables import metadata

    url = f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}"
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logger"] = False
    assert [r.revision for r in ScriptDirectory.from_config(config).walk_revisions()] == ["0001_initial"]
    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) == set(EXPECTED_COLUMNS) | {"alembic_version"}
        for name, columns in EXPECTED_COLUMNS.items():
            assert [c["name"] for c in inspector.get_columns(name)] == columns.split(), name
        with engine.connect() as conn:
            context = MigrationContext.configure(conn, opts={"compare_type": True, "target_metadata": metadata})
            assert compare_metadata(context, metadata) == []
            assert context.get_current_revision() == "0001_initial"
    finally:
        engine.dispose()
    command.downgrade(config, "base")
    engine = create_engine(url)
    try:
        assert inspect(engine).get_table_names() == ["alembic_version"]
    finally:
        engine.dispose()


def test_alembic_ini_holds_no_database_url():
    text = (REPO_ROOT / "alembic.ini").read_text(encoding="utf-8")
    assert "script_location = %(here)s/migrations" in text
    assert not re.search(r"^sqlalchemy\.url\s*=\s*\S", text, re.M)
    env_py = (REPO_ROOT / "migrations" / "env.py").read_text(encoding="utf-8")
    assert "load_settings().db_url" in env_py and "target_metadata = metadata" in env_py


# =========================================================================================
# 13. Every stub exists with the exact ADR signature (names only; never NotImplementedError)
# =========================================================================================
_SIGNOFF = "launch_agents.signoff"
_REPO = "launch_agents.persistence.repository:Repository"
_ACC = "launch_agents.persistence.accounts:AccountsRepository"
_TEAMR = "launch_agents.persistence.team:TeamRepository"
_AUTH = "launch_agents.accounts:AuthService"
_TEAMS = "launch_agents.team:TeamService"
_BILL = "launch_agents.billing:BillingService"
_ADMIN = "launch_agents.admin:AdminService"
_WEB = "launch_agents.workflows.website:WebsiteService"
_LEGAL = "launch_agents.workflows.legal:LegalService"
_CASE = "launch_agents.workflows.case:CaseService"
_ENQUEUE = "kind payload case_id user_id run_at max_attempts dedupe_key"
_LEGAL_METHODS = {
    "cap_table": "access", "cap_table_csv": "access", "cap_table_xlsx": "access", "generate_documents": "access",
    "regenerate_if_drafted": "access", "list_documents": "access", "get_document": "access document_id",
    "sign": "access document_id req", "edit": "access document_id req", "signed_pdf": "access document_id",
    "docx": "access document_id", "audit": "access", "legal_complete": "access",
}
_WEBSITE_METHODS = {
    "request_build": "access change_request", "request_deploy": "access override_qa",
    "run_build": "case_id change_request actor", "run_deploy": "case_id actor override_qa", "latest": "access",
    "preview_file": "access path", "download_zip": "access",
}

STUB_SIGNATURES: dict[str, str] = {
    # rules (T-002, T-003)
    "launch_agents.rules.validation:apply_vesting_defaults": "facts",
    "launch_agents.rules.validation:missing_facts": "facts",
    "launch_agents.rules.validation:validate_facts": "facts",
    "launch_agents.rules.cap_table:build_cap_table": "facts",
    "launch_agents.rules.cap_table:allocate_shares": "percents total",
    "launch_agents.rules.cap_table:vesting_schedule": "total vesting_months cliff_months start",
    "launch_agents.rules.exports:cap_table_csv": "cap",
    "launch_agents.rules.exports:cap_table_xlsx": "cap",
    # sign-off (T-004)
    f"{_SIGNOFF}:create_document": "case_id draft now",
    f"{_SIGNOFF}:sign": "doc founder_id version evidence now",
    f"{_SIGNOFF}:edit": "doc editor_id version new_content evidence now",
    f"{_SIGNOFF}:regenerate": "doc draft now actor",
    f"{_SIGNOFF}:is_legal_complete": "docs",
    # persistence (T-005 and the per-area tickets)
    "launch_agents.persistence.engine:create_db_engine": "url",
    "launch_agents.persistence.engine:init_db": "engine",
    "launch_agents.persistence.engine:schema_is_current": "engine",
    f"{_REPO}.__init__": "engine",
    f"{_REPO}.transaction": "",
    f"{_REPO}.create_case": "created_by facts state",
    f"{_REPO}.get_case": "case_id",
    f"{_REPO}.list_cases": "case_ids",
    f"{_REPO}.save_case": "case",
    f"{_REPO}.set_billing_user": "case_id user_id",
    f"{_REPO}.delete_case": "case_id",
    f"{_REPO}.append_messages": "case_id messages",
    f"{_REPO}.list_messages": "case_id after_seq limit",
    f"{_REPO}.save_document": "doc expected_version created_by",
    f"{_REPO}.get_document": "document_id",
    f"{_REPO}.list_documents": "case_id",
    f"{_REPO}.delete_document": "document_id",
    f"{_REPO}.append_audit": "entries",
    f"{_REPO}.list_audit": "case_id document_id",
    f"{_REPO}.set_checklist_item": "case_id item_id done updated_by",
    f"{_REPO}.get_checklist": "case_id",
    f"{_REPO}.save_site_build": "build",
    f"{_REPO}.get_site_build": "build_id",
    f"{_REPO}.latest_site_build": "case_id",
    f"{_REPO}.list_site_builds": "case_id",
    f"{_ACC}.__init__": "engine",
    f"{_ACC}.create_user": "email full_name password_hash",
    f"{_ACC}.get_user": "user_id",
    f"{_ACC}.find_user_by_email": "email",
    f"{_ACC}.get_password_hash": "user_id",
    f"{_ACC}.set_password_hash": "user_id h",
    f"{_ACC}.update_user": "user_id fields",
    f"{_ACC}.delete_user": "user_id",
    f"{_ACC}.create_session": "token_hash user_id expires_at ip user_agent",
    f"{_ACC}.get_session": "token_hash",
    f"{_ACC}.touch_session": "token_hash now expires_at",
    f"{_ACC}.revoke_session": "token_hash",
    f"{_ACC}.revoke_user_sessions": "user_id except_hash",
    f"{_ACC}.create_token": "token_hash user_id purpose expires_at",
    f"{_ACC}.use_token": "token_hash purpose now",
    f"{_ACC}.list_users": "query offset limit",
    f"{_TEAMR}.__init__": "engine",
    f"{_TEAMR}.add_member": "m",
    f"{_TEAMR}.get_membership": "case_id user_id",
    f"{_TEAMR}.list_members": "case_id",
    f"{_TEAMR}.member_case_ids": "user_id",
    f"{_TEAMR}.update_member": "case_id user_id fields",
    f"{_TEAMR}.remove_member": "case_id user_id",
    f"{_TEAMR}.create_invite": "invite token_hash",
    f"{_TEAMR}.find_invite_by_token": "token_hash",
    f"{_TEAMR}.list_invites": "case_id",
    f"{_TEAMR}.mark_invite": "invite_id accepted_at revoked_at",
    "launch_agents.persistence.email_outbox:EmailOutboxRepository.__init__": "engine",
    "launch_agents.persistence.email_outbox:EmailOutboxRepository.add": "message user_id case_id dedupe_key",
    "launch_agents.persistence.email_outbox:EmailOutboxRepository.get": "outbox_id",
    "launch_agents.persistence.email_outbox:EmailOutboxRepository.mark_sent": "outbox_id provider_id now",
    "launch_agents.persistence.email_outbox:EmailOutboxRepository.mark_failed": "outbox_id error now",
    "launch_agents.persistence.email_outbox:EmailOutboxRepository.list_recent": "status limit",
    "launch_agents.persistence.billing:BillingRepository.__init__": "engine",
    "launch_agents.persistence.jobs:JobsRepository.__init__": "engine",
    "launch_agents.persistence.limits:LimitsRepository.__init__": "engine",
    "launch_agents.persistence.privacy:PrivacyQueries.__init__": "engine",
    "launch_agents.persistence.admin:AdminQueries.__init__": "engine",
    # accounts, team, access (T-026, T-027)
    "launch_agents.accounts:hash_password": "password",
    "launch_agents.accounts:verify_password": "stored_hash password",
    "launch_agents.accounts:needs_rehash": "stored_hash",
    "launch_agents.accounts:check_password_policy": "password email",
    f"{_AUTH}.__init__": "accounts mailer settings clock",
    f"{_AUTH}.signup": "email password full_name ctx",
    f"{_AUTH}.login": "email password ctx",
    f"{_AUTH}.logout": "raw_token",
    f"{_AUTH}.resolve_session": "raw_token touch",
    f"{_AUTH}.request_email_verification": "user",
    f"{_AUTH}.verify_email": "raw_token",
    f"{_AUTH}.request_password_reset": "email ctx",
    f"{_AUTH}.reset_password": "raw_token new_password",
    f"{_AUTH}.change_password": "user current new keep_session",
    f"{_AUTH}.update_profile": "user full_name",
    f"{_TEAMS}.__init__": "team accounts repo mailer settings clock",
    f"{_TEAMS}.add_owner": "case_id user founder_id",
    f"{_TEAMS}.members": "access",
    f"{_TEAMS}.invite": "access email founder_id",
    f"{_TEAMS}.list_invites": "access",
    f"{_TEAMS}.revoke_invite": "access invite_id",
    f"{_TEAMS}.preview_invite": "raw_token",
    f"{_TEAMS}.accept_invite": "raw_token user",
    f"{_TEAMS}.link_founder": "access user_id founder_id",
    f"{_TEAMS}.remove_member": "access user_id",
    "launch_agents.access:authorize_case": "ctx case_id permission team repo entitlements",
    # email (T-028)
    "launch_agents.email:render_email": "template data brand_name base_url",
    "launch_agents.email:OutboxMailer.__init__": "outbox jobs settings",
    "launch_agents.email:OutboxMailer.send": "template to data user_id case_id dedupe_key",
    "launch_agents.email:send_outbox_email": "job ctx outbox sender",
    "launch_agents.email:ConsoleEmailSender.send": "message",
    "launch_agents.email:FileDropEmailSender.__init__": "path",
    "launch_agents.email:FileDropEmailSender.send": "message",
    "launch_agents.adapters.smtp_email:SmtpEmailSender.__init__": "settings smtp_factory",
    "launch_agents.adapters.smtp_email:SmtpEmailSender.send": "message",
    # billing (T-029)
    f"{_BILL}.__init__": "billing accounts gateway settings usage clock",
    f"{_BILL}.plans": "",
    f"{_BILL}.subscription": "user",
    f"{_BILL}.overview": "user",
    f"{_BILL}.start_checkout": "user plan interval",
    f"{_BILL}.change_plan": "user plan interval",
    f"{_BILL}.portal_url": "user",
    f"{_BILL}.handle_webhook": "payload signature_header",
    f"{_BILL}.complete_test_checkout": "session_id",
    f"{_BILL}.check_prices": "",
    "launch_agents.billing:DbEntitlements.__init__": "billing plans",
    "launch_agents.billing:DbEntitlements.for_user": "user_id",
    "launch_agents.billing:price_id_for": "settings plan interval",
    "launch_agents.billing:plan_for_price": "settings price_id",
    "launch_agents.adapters.stripe_payments:StripePaymentGateway.__init__": "settings client",
    "launch_agents.adapters.stripe_payments:StripePaymentGateway.create_customer": "email user_id",
    "launch_agents.adapters.stripe_payments:StripePaymentGateway.create_checkout_session":
        "customer_id price_id user_id success_url cancel_url",
    "launch_agents.adapters.stripe_payments:StripePaymentGateway.create_portal_session": "customer_id return_url",
    "launch_agents.adapters.stripe_payments:StripePaymentGateway.parse_webhook": "payload signature_header",
    "launch_agents.adapters.stripe_payments:StripePaymentGateway.change_subscription_price": "subscription_id price_id",
    "launch_agents.adapters.stripe_payments:StripePaymentGateway.price_amount": "price_id",
    # jobs (T-030)
    "launch_agents.jobs:DbJobRunner.__init__": "jobs clock",
    "launch_agents.jobs:DbJobRunner.enqueue": _ENQUEUE,
    "launch_agents.jobs:DbJobRunner.get": "job_id",
    "launch_agents.jobs:DbJobRunner.list_for_case": "case_id limit",
    "launch_agents.jobs:DbJobRunner.retry": "job_id",
    "launch_agents.jobs:Worker.__init__": "jobs registry worker_id clock lease_s poll_interval_s",
    "launch_agents.jobs:Worker.run_once": "",
    "launch_agents.jobs:Worker.run_forever": "stop",
    "launch_agents.jobs:Scheduler.__init__": "runner clock",
    "launch_agents.jobs:Scheduler.tick": "",
    "launch_agents.jobs:start_embedded_worker": "services",
    "launch_agents.ports.jobs:InlineJobRunner.enqueue": _ENQUEUE,
    "launch_agents.ports.jobs:JobRegistry.register": "kind handler",
    "launch_agents.ports.jobs:JobRegistry.handler": "kind",
    # pdf (T-031)
    "launch_agents.pdf:render_signed_pdf": "doc company_name signers audit generated_at brand_name",
    "launch_agents.pdf:render_docx": "doc company_name brand_name",
    "launch_agents.pdf:markdown_blocks": "content",
    # security (T-032)
    "launch_agents.security:issue_csrf_token": "secret session_key",
    "launch_agents.security:check_csrf": "method path header_token cookie_token origin settings",
    "launch_agents.security:security_headers": "path settings",
    "launch_agents.security:RateLimiter.__init__": "limits enabled clock",
    "launch_agents.security:RateLimiter.hit": "cls keys",
    "launch_agents.security:MeteredLLM.__init__": "inner limits user_id case_id monthly_limit clock",
    "launch_agents.security:scrub": "text",
    # observability (T-033)
    "launch_agents.observability:configure_logging": "settings",
    "launch_agents.observability:log_context": "fields",
    "launch_agents.observability:current_request_id": "",
    "launch_agents.observability:load_error_reporter": "dotted",
    "launch_agents.observability:report_error": "exc context",
    "launch_agents.observability:RequestContextMiddleware.__init__": "app",
    # LLM providers (T-024, T-025) and selection (T-001)
    "launch_agents.llm.claude_code:ClaudeCodeProvider.__init__": "settings runner binary",
    "launch_agents.llm.claude_code:ClaudeCodeProvider.complete": "request",
    "launch_agents.llm.claude_code:ClaudeCodeProvider.complete_json": "request schema",
    "launch_agents.llm.claude_code:find_claude_binary": "settings home",
    "launch_agents.llm.anthropic_provider:AnthropicProvider.__init__": "settings client",
    "launch_agents.llm.anthropic_provider:AnthropicProvider.complete_json": "request schema",
    "launch_agents.llm.openai_compat:OpenAICompatibleProvider.__init__": "settings preset chat_model",
    "launch_agents.llm.openai_compat:OpenAICompatibleProvider.complete_json": "request schema",
    "launch_agents.llm:get_llm": "settings",
    "launch_agents.llm:FakeLLM.__init__": "handlers include_defaults",
    "launch_agents.llm:FakeLLM.register": "task handler",
    "launch_agents.llm:FakeLLM.script": "task responses",
    "launch_agents.config:load_settings": "env",
    # agents (T-006..T-010, T-012)
    "launch_agents.agents.law:LawAgent.handle": "ctx",
    "launch_agents.agents.law:draft_documents": "facts cap_table today",
    "launch_agents.agents.law:spot_legal_issues": "facts state today",
    "launch_agents.agents.name:NameAgent.handle": "ctx",
    "launch_agents.agents.name:suggest_names": "facts llm count",
    "launch_agents.agents.name:check_candidate": "suggestion checker state_code now",
    "launch_agents.adapters.rdap:RdapDomainChecker.__init__": "client timeout_s",
    "launch_agents.adapters.rdap:RdapDomainChecker.check": "domain",
    "launch_agents.agents.website:WebsiteAgent.handle": "ctx",
    "launch_agents.agents.website:generate_content": "facts llm",
    "launch_agents.agents.website:revise_content": "content change_request facts llm",
    "launch_agents.agents.website:fix_content": "content issues facts llm",
    "launch_agents.agents.website:render_site": "content",
    "launch_agents.agents.website:required_pages": "facts",
    "launch_agents.adapters.netlify:NetlifySiteHost.__init__": "token client poll_timeout_s",
    "launch_agents.adapters.netlify:NetlifySiteHost.deploy": "site_slug bundle",
    "launch_agents.agents.qa:deterministic_checks": "bundle facts",
    "launch_agents.agents.qa:run_qa": "bundle facts llm round now",
    "launch_agents.agents.qa:qa_summary_message": "report",
    "launch_agents.agents.guide:GuideAgent.handle": "ctx",
    "launch_agents.agents.guide:build_guide": "facts chosen_domain deployed_url",
    "launch_agents.agents.manager:ManagerAgent.handle": "ctx",
    "launch_agents.agents.manager:next_question": "result",
    "launch_agents.agents.manager:facts_summary": "facts",
    "launch_agents.agents.manager:manager_greeting": "",
    "launch_agents.orchestrator:handle_turn": "turn deps",
    "launch_agents.orchestrator:build_graph": "deps",
    # pipeline and services (T-013, T-014, T-015)
    "launch_agents.pipelines.website:build_site": "facts llm previous change_request now",
    "launch_agents.pipelines.website:deploy_build": "build host site_slug override_qa",
    f"{_WEB}.__init__": "repo llm_for host jobs clock",
    **{f"{_WEB}.{m}": p for m, p in _WEBSITE_METHODS.items()},
    "launch_agents.workflows.website:register_website_jobs": "registry service",
    f"{_LEGAL}.__init__": "repo accounts team notifier clock",
    **{f"{_LEGAL}.{m}": p for m, p in _LEGAL_METHODS.items()},
    **{f"launch_agents.workflows.ports:LegalServicePort.{m}": p for m, p in _LEGAL_METHODS.items()},
    **{f"launch_agents.workflows.ports:WebsiteServicePort.{m}": p for m, p in _WEBSITE_METHODS.items()},
    f"{_CASE}.__init__": "repo team turn_handler agent_deps legal website jobs entitlements scrubber clock today",
    f"{_CASE}.create_case": "ctx",
    f"{_CASE}.list_cases": "ctx",
    f"{_CASE}.get_view": "access",
    f"{_CASE}.list_messages": "access after_seq",
    f"{_CASE}.post_message": "access text",
    f"{_CASE}.choose_name": "access name domain",
    f"{_CASE}.recheck_names": "access",
    f"{_CASE}.get_guide": "access",
    f"{_CASE}.set_guide_item": "access item_id done",
    f"{_CASE}.delete_case": "access",
    # notifications, privacy, admin (T-035, T-037, T-038)
    "launch_agents.notifications:EmailNotifier.__init__": "repo team accounts mailer settings",
    "launch_agents.notifications:EmailNotifier.signatures_needed": "case_id document founder_ids",
    "launch_agents.notifications:EmailNotifier.document_executed": "case_id document",
    "launch_agents.notifications:ReminderSweep.__init__": "repo team accounts mailer today",
    "launch_agents.notifications:ReminderSweep.run": "job ctx",
    "launch_agents.notifications:register_notification_jobs": "registry sweep",
    "launch_agents.privacy:PrivacyService.__init__": "queries repo team accounts billing settings clock",
    "launch_agents.privacy:PrivacyService.export_zip": "user",
    "launch_agents.privacy:PrivacyService.delete_account": "user password confirm",
    f"{_ADMIN}.__init__": "queries jobs accounts clock price_checks",
    f"{_ADMIN}.users": "query page plan",
    f"{_ADMIN}.companies": "query page",
    f"{_ADMIN}.usage": "month",
    f"{_ADMIN}.jobs": "status page",
    f"{_ADMIN}.emails": "status page",
    f"{_ADMIN}.system": "",
    f"{_ADMIN}.retry_job": "admin job_id",
    # composition, API, demo, devtools (T-016, T-011)
    "launch_agents.composition:build_services": "settings jobs",
    "launch_agents.api.app:create_app": "services settings",
    "launch_agents.api.deps:get_services": "request",
    "launch_agents.api.deps:require_case": "permission",
    "launch_agents.api.deps:rate_limit": "cls",
    "launch_agents.demo:seed_case": "settings stage plan",
    "launch_agents.devtools.ui_run:running_app": "seed_stage plan demo_mode env",
    "launch_agents.devtools.ui_run:login": "page app who",
    "launch_agents.devtools.ui_run:build_frontend": "force",
    "launch_agents.devtools.ui_run:capture_matrix": "browser url name out_dir prepare storage_state",
    "launch_agents.devtools.ui_run:assert_no_horizontal_scroll": "page",
    "launch_agents.devtools.ui_run:assert_no_raw_json": "page",
}

# Parameters that the ADRs declare keyword-only (after "*").
KEYWORD_ONLY = {
    f"{_SIGNOFF}:sign": {"evidence", "now"}, f"{_SIGNOFF}:edit": {"evidence", "now"},
    f"{_SIGNOFF}:create_document": {"now"}, f"{_SIGNOFF}:regenerate": {"now", "actor"},
    f"{_REPO}.create_case": {"created_by", "facts", "state"},
    f"{_REPO}.save_document": {"expected_version", "created_by"},
    "launch_agents.agents.qa:run_qa": {"round", "now"},
    "launch_agents.agents.guide:build_guide": {"chosen_domain", "deployed_url"},
    "launch_agents.pdf:render_signed_pdf": {"company_name", "signers", "audit", "generated_at", "brand_name"},
    "launch_agents.pdf:render_docx": {"company_name", "brand_name"},
    "launch_agents.composition:build_services": {"jobs"},
    "launch_agents.demo:seed_case": {"plan"},
    f"{_CASE}.__init__": {"turn_handler", "agent_deps", "legal", "website", "jobs", "entitlements", "scrubber",
                          "clock", "today"},
    "launch_agents.access:authorize_case": {"team", "repo", "entitlements"},
    "launch_agents.llm.claude_code:ClaudeCodeProvider.__init__": {"runner", "binary"},
    "launch_agents.llm.openai_compat:OpenAICompatibleProvider.__init__": {"preset", "chat_model"},
}


def _resolve(spec: str):
    module_name, qualname = spec.split(":")
    obj = importlib.import_module(module_name)
    for part in qualname.split("."):
        obj = getattr(obj, part)
    return obj


@pytest.mark.parametrize("spec", list(STUB_SIGNATURES))
def test_stub_signature(spec):
    parameters = [p for name, p in inspect.signature(_resolve(spec)).parameters.items() if name != "self"]
    expected = STUB_SIGNATURES[spec].split()
    names = [p.name for p in parameters]
    assert names[: len(expected)] == expected, f"{spec}: {names}"
    for extra in parameters[len(expected):]:  # later tickets may only add optional parameters
        assert extra.default is not inspect.Parameter.empty or extra.kind in (
            inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL), f"{spec}: {extra.name}"
    for name in KEYWORD_ONLY.get(spec, ()):
        assert next(p for p in parameters if p.name == name).kind == inspect.Parameter.KEYWORD_ONLY, f"{spec}: {name}"


def test_stub_classes_constants_and_types_exist():
    from launch_agents.adapters.stripe_payments import StripePaymentGateway
    from launch_agents.agents.law import LawAgent, LawIntent
    from launch_agents.agents.manager import ManagerAgent, ManagerExtraction, RouteDecision
    from launch_agents.agents.name import NameAgent, NameIntent, NameSuggestion, NameSuggestions
    from launch_agents.agents.qa import QaLlmReview
    from launch_agents.agents.website import WebsiteAgent, WebsiteIntent
    from launch_agents.agents.guide import GuideAgent
    from launch_agents.composition import Services
    from launch_agents.demo import DEMO_STAGES, SeedResult
    from launch_agents.devtools.ui_run import DEMO_PASSWORD, DEMO_TODAY, RunningApp
    from launch_agents.email import TEMPLATE_DATA_KEYS
    from launch_agents.notifications import ReminderSweep
    from launch_agents.pdf import SignerInfo
    from launch_agents.persistence.accounts import SessionRecord
    from launch_agents.persistence.email_outbox import OutboxEmail
    from launch_agents.pipelines.website import PipelineResult
    from launch_agents.privacy import DeletionReport
    from launch_agents.admin import Page, SystemInfo
    from launch_agents.security import RATE_LIMITS, ScrubResult
    from launch_agents.signoff import SignOffOutcome
    from launch_agents.agents.base import Specialist

    for cls, agent_id in ((LawAgent, AgentId.LAW), (NameAgent, AgentId.NAME), (WebsiteAgent, AgentId.WEBSITE),
                          (GuideAgent, AgentId.GUIDE), (ManagerAgent, AgentId.MANAGER)):
        agent = cls()  # no-argument constructor (ADR-0009)
        assert agent.agent_id == agent_id and isinstance(agent, Specialist)
    assert list(ManagerExtraction.model_fields) == ["facts", "confirms_summary"]
    assert list(RouteDecision.model_fields) == ["target", "reason"]
    assert list(LawIntent.model_fields) == ["intent", "topic"]
    assert list(NameIntent.model_fields) == ["intent", "name", "index"]
    assert list(NameSuggestion.model_fields) == ["name", "rationale"] and list(NameSuggestions.model_fields) == ["names"]
    assert list(WebsiteIntent.model_fields) == ["intent", "change_request", "override_qa", "requirements"]
    assert list(QaLlmReview.model_fields) == ["issues"]
    assert list(PipelineResult.model_fields) == ["content", "bundle", "reports", "passed", "fix_rounds"]
    assert list(SignOffOutcome.model_fields) == ["ok", "document", "audit", "invalidated", "error"]
    assert list(SignerInfo.model_fields) == ["full_name", "email"]
    assert list(ScrubResult.model_fields) == ["text", "redactions"]
    assert list(SessionRecord.model_fields)[:2] == ["token_hash", "user_id"] and "to_email" in OutboxEmail.model_fields
    assert DeletionReport and Page and SystemInfo and ReminderSweep.THRESHOLDS == (14, 7, 2)
    assert set(RATE_LIMITS) == {"auth", "email", "llm", "invite"}
    assert [(r.name, r.limit, r.window_s) for r in RATE_LIMITS["auth"]] == [("ip", 10, 900), ("email", 5, 900)]
    assert TEMPLATE_DATA_KEYS[EmailTemplate.DEADLINE_83B_REMINDER] == {"founder_name", "company_name", "deadline",
                                                                       "days_left", "link"}
    assert set(TEMPLATE_DATA_KEYS) == set(EmailTemplate)
    assert DEMO_STAGES == ("account", "new", "facts", "names", "legal", "signed", "website", "complete")
    assert [f.name for f in dataclasses.fields(SeedResult)] == ["case_id", "users"]
    assert [f.name for f in dataclasses.fields(RunningApp)] == ["base_url", "db_url", "case_id", "users", "email_drop"]
    assert (DEMO_TODAY, DEMO_PASSWORD) == (date(2026, 11, 23), "demo-password-2026")
    assert [f.name for f in dataclasses.fields(Services)] == (
        "settings engine repo accounts team_repo auth team billing entitlements case legal website jobs job_registry "
        "mailer notifier privacy admin limiter llm domain_checker host payments").split()
    assert StripePaymentGateway(load_settings({"STRIPE_SECRET_KEY": "sk_live_x"})).live is True
    assert StripePaymentGateway(load_settings({"STRIPE_SECRET_KEY": "sk_test_x"})).live is False


def test_route_modules_expose_empty_routers():
    from fastapi import APIRouter

    for name in ("cases", "jobs", "legal", "website", "auth", "account", "team", "billing", "admin"):
        module = importlib.import_module(f"launch_agents.api.routes.{name}")
        assert isinstance(module.router, APIRouter)


def test_running_app_reads_the_email_drop(tmp_path):
    from launch_agents.devtools.ui_run import RunningApp

    drop = tmp_path / "emails.jsonl"
    drop.write_text(json.dumps({"to": "bob@example.com", "subject": "a"}) + "\n" +
                    json.dumps({"to": "alice@example.com", "subject": "b"}) + "\n", encoding="utf-8")
    app = RunningApp(base_url="http://127.0.0.1:1", db_url="sqlite://", case_id=None, users={}, email_drop=drop)
    assert [e["subject"] for e in app.read_emails()] == ["a", "b"]
    assert [e["subject"] for e in app.read_emails(to="BOB@example.com")] == ["a"]


# =========================================================================================
# 14. create_app skeleton: health, error envelope, SPA fallback
# =========================================================================================
def _client(tmp_path=None, **settings_overrides):
    from fastapi.testclient import TestClient

    from launch_agents.api.app import create_app

    settings = load_settings(_test_env())
    if settings_overrides:
        settings = settings.model_copy(update=settings_overrides)
    app = create_app(settings=settings)
    return app, TestClient(app)


def test_health_without_services():
    app, client = _client()
    assert app.state.services is None
    response = client.get("/api/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert re.match(r"^[A-Za-z0-9-]{8,64}$", response.headers["X-Request-ID"])
    echoed = client.get("/api/health", headers={"X-Request-ID": "abcd-1234-efgh"})
    assert echoed.headers["X-Request-ID"] == "abcd-1234-efgh"


NEW_ERRORS = [
    ("AuthRequiredError", 401), ("InvalidCredentialsError", 401), ("ForbiddenError", 403),
    ("EmailNotVerifiedError", 403), ("CsrfError", 403), ("PlanRequiredError", 402), ("RateLimitedError", 429),
    ("UsageLimitError", 429), ("ConflictError", 409), ("TokenInvalidError", 400), ("NotExecutedError", 409),
    ("PaymentProviderError", 502), ("WebhookSignatureError", 400), ("RetryableError", 503),
    ("NotFoundError", 404), ("StaleVersionError", 409), ("LLMOutputError", 502),
]


def test_error_envelope_for_every_error():
    app, client = _client()

    @app.get("/api/test/raise/{name}")
    def raise_error(name: str):
        raise getattr(errors_module, name)("Friendly words.", details={"retry_after_s": 240, "x": 1})

    for name, status in NEW_ERRORS:
        response = client.get(f"/api/test/raise/{name}")
        cls = getattr(errors_module, name)
        assert response.status_code == status, name
        assert response.json() == {"error": {"code": cls.code, "message": "Friendly words.",
                                             "details": {"retry_after_s": 240, "x": 1}}}, name
    assert client.get("/api/test/raise/RateLimitedError").headers["Retry-After"] == "240"


def test_unexpected_errors_and_validation_errors():
    from fastapi import Body

    app, client = _client()

    @app.get("/api/test/crash")
    def crash():
        raise RuntimeError("database password is hunter2")

    @app.post("/api/test/body")
    def body(text: str = Body(..., embed=True, max_length=5)):
        return {"text": text}

    response = client.get("/api/test/crash", headers={"X-Request-ID": "req-crash-0001"})
    assert response.status_code == 500
    error = response.json()["error"]
    assert error == {"code": "internal", "message": "Something went wrong on our side. Please try again.",
                     "details": {}, "request_id": "req-crash-0001"}
    assert "hunter2" not in response.text and "Traceback" not in response.text
    invalid = client.post("/api/test/body", json={"text": "far too long"})
    assert invalid.status_code == 422 and invalid.json()["error"]["code"] == "invalid_request"
    assert invalid.json()["error"]["details"]["fields"][0]["field"] == "text"


def test_spa_fallback_and_json_404(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("nope", encoding="utf-8")
    _, client = _client(frontend_dist=str(dist))
    page = client.get("/app/x")
    assert page.status_code == 200 and "id=root" in page.text and page.headers["content-type"].startswith("text/html")
    assert client.get("/").text == page.text
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert "nope" not in client.get("/../secret.txt").text
    missing = client.get("/api/nope")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"
    assert client.post("/app/x").status_code in (404, 405)
    _, no_dist = _client(frontend_dist=str(tmp_path / "missing"))
    assert no_dist.get("/app/x").status_code == 404 and no_dist.get("/app/x").json()["error"]["code"] == "not_found"


def test_get_services_without_services_is_a_friendly_503():
    from fastapi import Depends

    from launch_agents.api.deps import get_services

    app, client = _client()

    @app.get("/api/test/services")
    def needs_services(services=Depends(get_services)):
        return {"ok": True}

    response = client.get("/api/test/services")
    assert response.status_code == 503 and response.json()["error"]["code"] == "temporarily_unavailable"


# =========================================================================================
# 15. .env.example
# =========================================================================================
CONFIG_ENV_VARS = (
    "APP_ENV APP_BASE_URL BRAND_NAME SECRET_KEY DEMO_MODE LAUNCH_FAKE_SERVICES LAUNCH_TODAY "
    "LLM_PROVIDER LLM_MODEL LLM_EFFORT LLM_TIMEOUT_S LLM_MAX_RETRIES ANTHROPIC_API_KEY DEEPSEEK_API_KEY GROQ_API_KEY "
    "LLM_API_KEY LLM_BASE_URL ANTHROPIC_REFUSAL_FALLBACK CLAUDE_CODE_PATH CLAUDE_CODE_TIMEOUT_S "
    "DOMAIN_CHECKER HOSTING_PROVIDER NETLIFY_AUTH_TOKEN "
    "EMAIL_PROVIDER EMAIL_FROM EMAIL_DROP_FILE SMTP_HOST SMTP_PORT SMTP_USERNAME SMTP_PASSWORD SMTP_STARTTLS "
    "PAYMENTS_PROVIDER STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET STRIPE_PRICE_LAUNCH_MONTHLY STRIPE_PRICE_LAUNCH_YEARLY "
    "STRIPE_PRICE_TEAM_MONTHLY STRIPE_PRICE_TEAM_YEARLY BILLING_YEARLY_ENABLED SUPPORT_EMAIL "
    "LAUNCH_DB_URL JOBS_EMBEDDED_WORKER SESSION_IDLE_DAYS SESSION_MAX_DAYS LAUNCH_CORS_ORIGINS TRUSTED_PROXY_COUNT "
    "RATE_LIMITS_ENABLED LOG_FORMAT LOG_LEVEL ERROR_REPORTER FRONTEND_DIST"
).split()
PLAN_ENV_VARS = [f"PLAN_{p}_{f}" for p in ("FREE", "LAUNCH", "TEAM")
                 for f in ("PRICE_MONTH_CENTS", "PRICE_YEAR_CENTS", "MAX_COMPANIES", "AI_MESSAGES")]
_VAR_LINE = re.compile(r"^(#\s*)?([A-Z][A-Z0-9_]+)=(.*)$")


def _env_example() -> list[str]:
    return (REPO_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()


def test_env_example_lists_every_variable_with_a_comment():
    lines = _env_example()
    active: dict[str, str] = {}
    commented: dict[str, str] = {}
    for i, line in enumerate(lines):
        match = _VAR_LINE.match(line)
        if not match:
            continue
        name, value = match.group(2), match.group(3)
        (commented if match.group(1) else active)[name] = value
        j = i - 1  # walk up over the variable lines of the same block to its comment
        while j >= 0 and _VAR_LINE.match(lines[j]):
            j -= 1
        assert j >= 0 and lines[j].startswith("#") and not lines[j].startswith("# ----"), f"{name} has no comment"
    for name in CONFIG_ENV_VARS:
        assert name in active, name
    for name in PLAN_ENV_VARS:
        assert name in commented and name not in active, name
    from launch_agents.config import _PLAN_FIELDS

    for plan_id, amounts in DEFAULT_PLAN_AMOUNTS.items():
        for suffix, field in _PLAN_FIELDS.items():
            assert commented[f"PLAN_{plan_id.value.upper()}_{suffix}"] == str(getattr(amounts, field))
    assert active["BRAND_NAME"] == "Charterly"
    assert "# LLM_MODEL_NAME=claude-haiku-5-5" in lines and "# LLM_MODEL_QA=claude-haiku-5-5" in lines
    known = set(CONFIG_ENV_VARS) | set(PLAN_ENV_VARS) | {"LAUNCH_TEST_POSTGRES_URL", "LLM_MODEL_NAME", "LLM_MODEL_QA",
                                                          "LLM_EFFORT_QA"}
    assert set(active) | set(commented) <= known


def test_env_example_groups_and_no_secrets():
    lines = _env_example()
    titles = [line.strip("# -").split(" (")[0] for line in lines if line.startswith("# ----")]
    assert titles == ["core", "LLM", "services", "email", "payments", "data and jobs", "security", "operations"]
    for line in lines:
        match = _VAR_LINE.match(line)
        if match and not match.group(1) and any(m in match.group(2) for m in ("KEY", "SECRET", "TOKEN", "PASSWORD")):
            assert match.group(3) == "", f"{match.group(2)} must be empty in .env.example"
    assert "sk_live_" not in "\n".join(lines).replace("sk_live_...", "")


def test_env_example_loads_as_development_settings():
    values = {}
    for line in _env_example():
        match = _VAR_LINE.match(line)
        if match and not match.group(1):
            values[match.group(2)] = match.group(3)
    s = load_settings(values)
    assert s.app_env == AppEnv.DEVELOPMENT and s.llm_provider == "fake" and s.brand_name == "Charterly"


# =========================================================================================
# 16. Brand guard (ADR-0039)
# =========================================================================================
def test_brand_name_is_spelled_out_only_in_domain_constants():
    offenders = []
    for path in PACKAGE_DIR.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "Charterly" in text and path.relative_to(PACKAGE_DIR).as_posix() != "domain/constants.py":
            offenders.append(path.relative_to(REPO_ROOT).as_posix())
    assert offenders == []
    assert "Charterly" in (PACKAGE_DIR / "domain" / "constants.py").read_text(encoding="utf-8")
    assert load_settings({"BRAND_NAME": "Other"}).brand_name == "Other"


# =========================================================================================
# 17. Test infrastructure: the ADR-0025 skip hook, postgres marker, fixtures
# =========================================================================================
def test_missing_package_detection(monkeypatch):
    from conftest import adr0025_skip_reason, missing_adr0025_package

    monkeypatch.setitem(sys.modules, "argon2", None)  # argon2 is not importable
    try:
        try:
            raise ModuleNotFoundError("No module named 'argon2'", name="argon2")
        except ModuleNotFoundError as inner:
            raise RuntimeError("collect failed") from inner
    except RuntimeError as outer:
        assert missing_adr0025_package(outer) == "argon2-cffi"
    # a missing submodule or a bad symbol is a real bug, never "not installed"
    assert missing_adr0025_package(ModuleNotFoundError("x", name="argon2.no_such_module")) is None
    assert missing_adr0025_package(ImportError("cannot import name 'Nope'", name="argon2")) is None
    assert missing_adr0025_package(ModuleNotFoundError("x", name="numpy")) is None
    assert adr0025_skip_reason("stripe") == "package stripe not installed (ADR-0025)"


def test_missing_package_detection_ignores_installed_packages(monkeypatch):
    from conftest import missing_adr0025_package

    monkeypatch.setitem(sys.modules, "docx", importlib.import_module("json"))  # stands in for an installed package
    assert missing_adr0025_package(ModuleNotFoundError("x", name="docx")) is None
    monkeypatch.setitem(sys.modules, "docx", None)
    assert missing_adr0025_package(ModuleNotFoundError("x", name="docx")) == "python-docx"


def test_bad_imports_from_installed_adr0025_packages_fail_not_skip(tmp_path):
    """A wrong symbol or submodule of an installed package must fail, at collection and in a test."""
    (tmp_path / "conftest.py").write_text((REPO_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8"),
                                          encoding="utf-8")
    (tmp_path / "pytest.ini").write_text("[pytest]\naddopts = -q\nmarkers =\n    postgres: pg\n", encoding="utf-8")
    # stand-in for an installed ADR-0025 package, so the test needs none of them installed
    pkg = tmp_path / "stripe"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("REAL = 1\n", encoding="utf-8")
    (tmp_path / "test_bad_symbol_at_collection.py").write_text(
        "from stripe import ThisSymbolDoesNotExist\n\ndef test_a():\n    pass\n", encoding="utf-8")
    (tmp_path / "test_bad_submodule_at_collection.py").write_text(
        "import stripe.no_such_module\n\ndef test_b():\n    pass\n", encoding="utf-8")
    (tmp_path / "test_bad_imports_in_tests.py").write_text(
        "def test_c():\n    from stripe import ThisSymbolDoesNotExist\n\n"
        "def test_d():\n    import stripe.no_such_module\n\n"
        "def test_e():\n    from stripe import REAL\n    assert REAL == 1\n", encoding="utf-8")
    env = {**os.environ, "LAUNCH_TEST_POSTGRES_URL": "", "PYTHONPATH": str(tmp_path)}
    result = subprocess.run([sys.executable, "-m", "pytest", "-rs", "-p", "no:cacheprovider",
                             "--continue-on-collection-errors", str(tmp_path)],
                            cwd=tmp_path, capture_output=True, text=True, timeout=120, env=env)
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "not installed (ADR-0025)" not in output
    assert "skipped" not in output
    assert "2 failed, 1 passed, 2 errors" in output, output


def test_collection_hook_skips_modules_needing_a_missing_package(tmp_path):
    (tmp_path / "conftest.py").write_text((REPO_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8"),
                                          encoding="utf-8")
    (tmp_path / "pytest.ini").write_text("[pytest]\naddopts = -q\nmarkers =\n    postgres: pg\n", encoding="utf-8")
    (tmp_path / "test_needs_stripe.py").write_text(
        "import sys\nsys.modules['stripe'] = None\nimport stripe\n\ndef test_x():\n    assert False\n", encoding="utf-8")
    (tmp_path / "test_lazy_reportlab.py").write_text(
        "import sys\n\ndef test_y():\n    sys.modules['reportlab'] = None\n    import reportlab\n", encoding="utf-8")
    (tmp_path / "test_plain.py").write_text(
        "import pytest\n\ndef test_ok():\n    assert True\n\n@pytest.mark.postgres\ndef test_pg():\n    assert False\n",
        encoding="utf-8")
    env = {**os.environ, "LAUNCH_TEST_POSTGRES_URL": ""}
    result = subprocess.run([sys.executable, "-m", "pytest", "-rs", "-p", "no:cacheprovider", str(tmp_path)],
                            cwd=tmp_path, capture_output=True, text=True, timeout=120, env=env)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "package stripe not installed (ADR-0025)" in output
    assert "package reportlab not installed (ADR-0025)" in output
    assert "1 passed, 3 skipped" in output


def test_shared_fixtures(sample_facts, today, settings, fake_payments, inline_jobs, fake_mailer, fake_notifier,
                         entitlements_free, entitlements_launch, entitlements_team, request_ctx, system_access,
                         fake_llm, fake_domain_checker, fake_site_host, sample_user):
    assert today == date(2026, 11, 23)
    assert [f.name for f in sample_facts.founders] == ["Alice Chen", "Bob Diaz"]
    assert sample_facts.founders[1].vesting_months is None and sample_facts.state == "WY"
    assert settings.app_env == AppEnv.TEST and settings.fake_services and settings.db_url.startswith("sqlite:///")
    assert settings.today == today
    assert fake_payments.base_url == "http://testserver" and isinstance(inline_jobs, InlineJobRunner)
    assert (entitlements_free.for_user("u").plan, entitlements_launch.for_user("u").plan,
            entitlements_team.for_user("u").plan) == (PlanId.FREE, PlanId.LAUNCH, PlanId.TEAM)
    ctx = request_ctx(user=sample_user)
    assert ctx.require_user() is sample_user and ctx.ip == "127.0.0.1"
    assert request_ctx(demo_mode=True, act_as_founder_id="f2").act_as_founder_id == "f2"
    access = system_access("case_1", PlanId.FREE)
    assert access.case_id == "case_1" and access.entitlements.plan == PlanId.FREE
    assert fake_mailer.sent == [] and fake_notifier.events == [] and fake_llm.calls == []
    assert fake_domain_checker.name == "fake" and fake_site_host.configured and sample_user.email_verified


def test_engine_and_repo_fixtures_skip_while_persistence_is_a_stub(request):
    try:
        repo = request.getfixturevalue("repo")
    except pytest.skip.Exception as skipped:
        assert "still a stub" in str(skipped)
        return
    assert repo.list_cases([]) == []  # pragma: no cover - once T-005 is merged


def test_pytest_ini():
    text = (REPO_ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert "testpaths = tests" in text and "addopts = -q" in text and "postgres:" in text


def test_settings_type_is_exported():
    assert Settings.model_config.get("frozen") is True
