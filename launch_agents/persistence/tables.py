"""Every table of the product on one ``MetaData`` (ADR-0027). Owned by T-001.

Portable column types only (``String``, ``Text``, ``Integer``, ``Boolean``,
``DateTime(timezone=True)``), so SQLite and PostgreSQL behave alike. JSON lives in ``Text``
columns; timestamps are UTC; ids are ``String(40)`` from ``new_id(prefix)``. Case-owned rows
cascade when a company is deleted; history that must outlive a user keeps the row and sets
the user reference to NULL.

``migrations/versions/0001_initial.py`` creates exactly this schema. A later schema change is
a new migration plus the matching change here, made by at most one ticket per wave.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
)

__all__ = [
    "NAMING_CONVENTION",
    "TABLE_NAMES",
    "admin_audit",
    "audit_log",
    "auth_tokens",
    "billing_events",
    "cases",
    "checklist_items",
    "document_versions",
    "documents",
    "email_outbox",
    "invites",
    "jobs",
    "llm_usage",
    "memberships",
    "messages",
    "metadata",
    "rate_limits",
    "sessions",
    "signatures",
    "site_builds",
    "subscriptions",
    "users",
    "worker_heartbeats",
]

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)

ID = 40  # length of ids from new_id(prefix)


def _ts(name: str, nullable: bool = False) -> Column:
    return Column(name, DateTime(timezone=True), nullable=nullable)


def _user_fk(name: str, *, nullable: bool, ondelete: str) -> Column:
    return Column(name, String(ID), ForeignKey("users.id", ondelete=ondelete), nullable=nullable)


def _case_fk(name: str = "case_id", *, nullable: bool = False, ondelete: str = "CASCADE") -> Column:
    return Column(name, String(ID), ForeignKey("cases.id", ondelete=ondelete), nullable=nullable)


# --- accounts (T-026) ---------------------------------------------------------------------
users = Table(
    "users",
    metadata,
    Column("id", String(ID), nullable=False),
    Column("email", String(254), nullable=False),  # lower-cased by the service
    Column("full_name", String(200), nullable=False),
    Column("password_hash", String(255), nullable=False),
    _ts("email_verified_at", nullable=True),
    Column("is_admin", Boolean, nullable=False),
    _ts("created_at"),
    _ts("updated_at"),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("email"),
)

sessions = Table(
    "sessions",
    metadata,
    Column("token_hash", String(64), nullable=False),  # SHA-256 hex of the raw token
    _user_fk("user_id", nullable=False, ondelete="CASCADE"),
    _ts("created_at"),
    _ts("last_seen_at"),
    _ts("expires_at"),
    _ts("revoked_at", nullable=True),
    Column("ip", String(64), nullable=True),
    Column("user_agent", String(512), nullable=True),
    PrimaryKeyConstraint("token_hash"),
    Index(None, "user_id"),
)

auth_tokens = Table(
    "auth_tokens",
    metadata,
    Column("token_hash", String(64), nullable=False),
    _user_fk("user_id", nullable=False, ondelete="CASCADE"),
    Column("purpose", String(32), nullable=False),  # verify_email | password_reset
    _ts("created_at"),
    _ts("expires_at"),
    _ts("used_at", nullable=True),
    PrimaryKeyConstraint("token_hash"),
    Index(None, "user_id", "purpose"),
)

# --- companies (T-005) ----------------------------------------------------------------------
cases = Table(
    "cases",
    metadata,
    Column("id", String(ID), nullable=False),
    _ts("created_at"),
    _ts("updated_at"),
    Column("facts_json", Text, nullable=False),
    Column("state_json", Text, nullable=False),
    _user_fk("created_by", nullable=True, ondelete="SET NULL"),
    _user_fk("billing_user_id", nullable=True, ondelete="SET NULL"),
    PrimaryKeyConstraint("id"),
    Index(None, "billing_user_id"),
)

# --- team (T-027) ---------------------------------------------------------------------------
memberships = Table(
    "memberships",
    metadata,
    _case_fk(),
    _user_fk("user_id", nullable=False, ondelete="CASCADE"),
    Column("role", String(16), nullable=False),  # owner | member
    Column("founder_id", String(16), nullable=True),
    _ts("joined_at"),
    PrimaryKeyConstraint("case_id", "user_id"),
    UniqueConstraint("case_id", "founder_id"),
)

invites = Table(
    "invites",
    metadata,
    Column("id", String(ID), nullable=False),
    _case_fk(),
    Column("email", String(254), nullable=False),
    Column("founder_id", String(16), nullable=True),
    Column("token_hash", String(64), nullable=False),
    Column("invited_by", String(ID), nullable=False),  # user id; kept as text (history)
    _ts("created_at"),
    _ts("expires_at"),
    _ts("accepted_at", nullable=True),
    _ts("revoked_at", nullable=True),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("token_hash"),
    Index(None, "case_id"),
)

# --- chat, documents, audit, checklist, site builds (T-005) ---------------------------------
messages = Table(
    "messages",
    metadata,
    Column("id", String(ID), nullable=False),
    _case_fk(),
    Column("seq", Integer, nullable=False),
    Column("role", String(16), nullable=False),
    Column("agent", String(32), nullable=True),
    Column("founder_id", String(16), nullable=True),
    Column("kind", String(32), nullable=False),
    Column("content", Text, nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("suggested_json", Text, nullable=False),
    _ts("created_at"),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("case_id", "seq"),
)

documents = Table(
    "documents",
    metadata,
    Column("id", String(ID), nullable=False),
    _case_fk(),
    Column("kind", String(64), nullable=False),
    Column("founder_id", String(16), nullable=True),
    Column("title", String(255), nullable=False),
    Column("version", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("status", String(32), nullable=False),
    Column("required_signers_json", Text, nullable=False),
    _ts("created_at"),
    _ts("updated_at"),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("case_id", "kind", "founder_id"),
)

document_versions = Table(
    "document_versions",
    metadata,
    Column("document_id", String(ID), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
    Column("version", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("created_by", String(64), nullable=False),
    _ts("created_at"),
    PrimaryKeyConstraint("document_id", "version"),
)

signatures = Table(
    "signatures",
    metadata,
    Column("document_id", String(ID), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
    Column("founder_id", String(16), nullable=False),
    Column("version", Integer, nullable=False),
    _ts("signed_at"),
    _user_fk("user_id", nullable=True, ondelete="SET NULL"),
    Column("typed_name", String(200), nullable=False),
    Column("consent_version", String(32), nullable=False),
    Column("ip", String(64), nullable=True),
    Column("user_agent", String(512), nullable=True),
    Column("content_sha256", String(64), nullable=False),
    _user_fk("acted_by_user_id", nullable=True, ondelete="SET NULL"),
    PrimaryKeyConstraint("document_id", "founder_id", "version"),
)

audit_log = Table(
    "audit_log",
    metadata,
    Column("id", Integer, autoincrement=True, nullable=False),
    _case_fk(),
    Column("document_id", String(ID), nullable=True),  # no FK: audit outlives a deleted document
    Column("actor", String(64), nullable=False),  # founder id, user id, "system" or an agent id
    Column("action", String(64), nullable=False),
    Column("from_version", Integer, nullable=True),
    Column("to_version", Integer, nullable=True),
    Column("detail_json", Text, nullable=False),
    _ts("at"),
    PrimaryKeyConstraint("id"),
    Index(None, "case_id", "id"),
)

checklist_items = Table(
    "checklist_items",
    metadata,
    _case_fk(),
    Column("item_id", String(64), nullable=False),
    Column("done", Boolean, nullable=False),
    Column("updated_by", String(64), nullable=True),
    _ts("updated_at"),
    PrimaryKeyConstraint("case_id", "item_id"),
)

site_builds = Table(
    "site_builds",
    metadata,
    Column("id", String(ID), nullable=False),
    _case_fk(),
    Column("version", Integer, nullable=False),
    Column("content_json", Text, nullable=False),
    Column("files_json", Text, nullable=False),
    Column("qa_reports_json", Text, nullable=False),
    Column("qa_passed", Boolean, nullable=False),
    Column("fix_rounds", Integer, nullable=False),
    Column("status", String(32), nullable=False),
    Column("deploy_url", String(512), nullable=True),
    Column("deploy_message", Text, nullable=True),
    Column("override_by", String(64), nullable=True),
    _ts("created_at"),
    _ts("updated_at"),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("case_id", "version"),
)

# --- billing (T-029) ------------------------------------------------------------------------
subscriptions = Table(
    "subscriptions",
    metadata,
    _user_fk("user_id", nullable=False, ondelete="CASCADE"),
    Column("plan", String(16), nullable=False),
    Column("interval", String(8), nullable=True),
    Column("status", String(16), nullable=False),
    _ts("current_period_end", nullable=True),
    Column("cancel_at_period_end", Boolean, nullable=False),
    Column("provider_customer_id", String(255), nullable=True),
    Column("provider_subscription_id", String(255), nullable=True),
    _ts("updated_at"),
    PrimaryKeyConstraint("user_id"),
    UniqueConstraint("provider_customer_id"),
)

billing_events = Table(
    "billing_events",
    metadata,
    Column("id", String(255), nullable=False),  # the provider's event id
    Column("type", String(100), nullable=False),
    _ts("received_at"),
    _ts("processed_at", nullable=True),
    Column("error", Text, nullable=True),
    Column("payload_json", Text, nullable=False),
    PrimaryKeyConstraint("id"),
)

# --- jobs (T-030) ---------------------------------------------------------------------------
jobs = Table(
    "jobs",
    metadata,
    Column("id", String(ID), nullable=False),
    Column("kind", String(64), nullable=False),
    Column("status", String(16), nullable=False),
    _case_fk(nullable=True),
    _user_fk("user_id", nullable=True, ondelete="SET NULL"),
    Column("payload_json", Text, nullable=False),
    Column("result_json", Text, nullable=True),
    Column("error", Text, nullable=True),
    Column("attempts", Integer, nullable=False),
    Column("max_attempts", Integer, nullable=False),
    _ts("run_at"),
    Column("locked_by", String(64), nullable=True),
    _ts("locked_until", nullable=True),
    Column("dedupe_key", String(255), nullable=True),
    _ts("created_at"),
    _ts("updated_at"),
    _ts("finished_at", nullable=True),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("dedupe_key"),
    Index(None, "status", "run_at"),
)

worker_heartbeats = Table(
    "worker_heartbeats",
    metadata,
    Column("worker_id", String(64), nullable=False),
    _ts("last_seen_at"),
    PrimaryKeyConstraint("worker_id"),
)

# --- email (T-028) --------------------------------------------------------------------------
email_outbox = Table(
    "email_outbox",
    metadata,
    Column("id", String(ID), nullable=False),
    Column("to_email", String(254), nullable=False),
    Column("template", String(64), nullable=False),
    Column("subject", String(255), nullable=False),
    Column("text_body", Text, nullable=False),
    Column("html_body", Text, nullable=False),
    Column("status", String(16), nullable=False),  # queued | sent | failed
    Column("attempts", Integer, nullable=False),
    _user_fk("user_id", nullable=True, ondelete="CASCADE"),
    _case_fk(nullable=True, ondelete="SET NULL"),
    Column("dedupe_key", String(255), nullable=True),
    Column("provider_id", String(255), nullable=True),
    Column("error", Text, nullable=True),
    _ts("created_at"),
    _ts("sent_at", nullable=True),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("dedupe_key"),
)

# --- limits and usage (T-032) ---------------------------------------------------------------
llm_usage = Table(
    "llm_usage",
    metadata,
    Column("id", Integer, autoincrement=True, nullable=False),
    _user_fk("user_id", nullable=True, ondelete="SET NULL"),
    _case_fk(nullable=True, ondelete="SET NULL"),
    Column("task", String(64), nullable=False),
    Column("provider", String(32), nullable=False),
    Column("model", String(100), nullable=True),
    Column("input_tokens", Integer, nullable=True),
    Column("output_tokens", Integer, nullable=True),
    Column("duration_ms", Integer, nullable=False),
    Column("ok", Boolean, nullable=False),
    _ts("at"),
    PrimaryKeyConstraint("id"),
    Index(None, "user_id", "at"),
)

rate_limits = Table(
    "rate_limits",
    metadata,
    Column("key", String(255), nullable=False),
    _ts("window_start"),
    Column("count", Integer, nullable=False),
    PrimaryKeyConstraint("key", "window_start"),
)

# --- admin (T-038) --------------------------------------------------------------------------
admin_audit = Table(
    "admin_audit",
    metadata,
    Column("id", Integer, autoincrement=True, nullable=False),
    Column("admin_user_id", String(ID), nullable=False),  # a user id, or "cli"
    Column("action", String(64), nullable=False),
    Column("target", String(255), nullable=False),
    Column("detail_json", Text, nullable=False),
    _ts("at"),
    PrimaryKeyConstraint("id"),
    Index(None, "at"),
)

TABLE_NAMES: tuple[str, ...] = tuple(sorted(metadata.tables))
