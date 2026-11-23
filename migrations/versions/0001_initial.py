"""Initial schema: every table of ADR-0027.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-23

Hand-written and frozen: it must keep creating exactly the schema of
``launch_agents/persistence/tables.py`` as of this revision (portable types only, explicit
constraint names that follow the metadata naming convention). Later schema changes are new
revisions (ADR-0027).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_audit",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("admin_user_id", sa.String(length=40), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_admin_audit"),
    )
    op.create_index("ix_admin_audit_at", "admin_audit", ["at"], unique=False)

    op.create_table(
        "billing_events",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_billing_events"),
    )

    op.create_table(
        "rate_limits",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key", "window_start", name="pk_rate_limits"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "worker_heartbeats",
        sa.Column("worker_id", sa.String(length=64), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("worker_id", name="pk_worker_heartbeats"),
    )

    op.create_table(
        "auth_tokens",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=40), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_auth_tokens_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash", name="pk_auth_tokens"),
    )
    op.create_index("ix_auth_tokens_user_id_purpose", "auth_tokens", ["user_id", "purpose"], unique=False)

    op.create_table(
        "cases",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("facts_json", sa.Text(), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=40), nullable=True),
        sa.Column("billing_user_id", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(["billing_user_id"], ["users.id"], name="fk_cases_billing_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_cases_created_by_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_cases"),
    )
    op.create_index("ix_cases_billing_user_id", "cases", ["billing_user_id"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_sessions_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash", name="pk_sessions"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)

    op.create_table(
        "subscriptions",
        sa.Column("user_id", sa.String(length=40), nullable=False),
        sa.Column("plan", sa.String(length=16), nullable=False),
        sa.Column("interval", sa.String(length=8), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("provider_customer_id", sa.String(length=255), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_subscriptions_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", name="pk_subscriptions"),
        sa.UniqueConstraint("provider_customer_id", name="uq_subscriptions_provider_customer_id"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("case_id", sa.String(length=40), nullable=False),
        sa.Column("document_id", sa.String(length=40), nullable=True),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("from_version", sa.Integer(), nullable=True),
        sa.Column("to_version", sa.Integer(), nullable=True),
        sa.Column("detail_json", sa.Text(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_audit_log_case_id_cases", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_log"),
    )
    op.create_index("ix_audit_log_case_id_id", "audit_log", ["case_id", "id"], unique=False)

    op.create_table(
        "checklist_items",
        sa.Column("case_id", sa.String(length=40), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("done", sa.Boolean(), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_checklist_items_case_id_cases", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("case_id", "item_id", name="pk_checklist_items"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("case_id", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("founder_id", sa.String(length=16), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("required_signers_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_documents_case_id_cases", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.UniqueConstraint("case_id", "kind", "founder_id", name="uq_documents_case_id_kind_founder_id"),
    )

    op.create_table(
        "email_outbox",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("to_email", sa.String(length=254), nullable=False),
        sa.Column("template", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("text_body", sa.Text(), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=40), nullable=True),
        sa.Column("case_id", sa.String(length=40), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("provider_id", sa.String(length=255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_email_outbox_case_id_cases", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_email_outbox_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_email_outbox"),
        sa.UniqueConstraint("dedupe_key", name="uq_email_outbox_dedupe_key"),
    )

    op.create_table(
        "invites",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("case_id", sa.String(length=40), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("founder_id", sa.String(length=16), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_invites_case_id_cases", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_invites"),
        sa.UniqueConstraint("token_hash", name="uq_invites_token_hash"),
    )
    op.create_index("ix_invites_case_id", "invites", ["case_id"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("case_id", sa.String(length=40), nullable=True),
        sa.Column("user_id", sa.String(length=40), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_by", sa.String(length=64), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_jobs_case_id_cases", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_jobs_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
        sa.UniqueConstraint("dedupe_key", name="uq_jobs_dedupe_key"),
    )
    op.create_index("ix_jobs_status_run_at", "jobs", ["status", "run_at"], unique=False)

    op.create_table(
        "llm_usage",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.String(length=40), nullable=True),
        sa.Column("case_id", sa.String(length=40), nullable=True),
        sa.Column("task", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_llm_usage_case_id_cases", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_llm_usage_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_llm_usage"),
    )
    op.create_index("ix_llm_usage_user_id_at", "llm_usage", ["user_id", "at"], unique=False)

    op.create_table(
        "memberships",
        sa.Column("case_id", sa.String(length=40), nullable=False),
        sa.Column("user_id", sa.String(length=40), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("founder_id", sa.String(length=16), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_memberships_case_id_cases", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_memberships_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("case_id", "user_id", name="pk_memberships"),
        sa.UniqueConstraint("case_id", "founder_id", name="uq_memberships_case_id_founder_id"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("case_id", sa.String(length=40), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("agent", sa.String(length=32), nullable=True),
        sa.Column("founder_id", sa.String(length=16), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("suggested_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_messages_case_id_cases", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
        sa.UniqueConstraint("case_id", "seq", name="uq_messages_case_id_seq"),
    )

    op.create_table(
        "site_builds",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("case_id", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("files_json", sa.Text(), nullable=False),
        sa.Column("qa_reports_json", sa.Text(), nullable=False),
        sa.Column("qa_passed", sa.Boolean(), nullable=False),
        sa.Column("fix_rounds", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("deploy_url", sa.String(length=512), nullable=True),
        sa.Column("deploy_message", sa.Text(), nullable=True),
        sa.Column("override_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_site_builds_case_id_cases", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_site_builds"),
        sa.UniqueConstraint("case_id", "version", name="uq_site_builds_case_id_version"),
    )

    op.create_table(
        "document_versions",
        sa.Column("document_id", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_document_versions_document_id_documents", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "version", name="pk_document_versions"),
    )

    op.create_table(
        "signatures",
        sa.Column("document_id", sa.String(length=40), nullable=False),
        sa.Column("founder_id", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=40), nullable=True),
        sa.Column("typed_name", sa.String(length=200), nullable=False),
        sa.Column("consent_version", sa.String(length=32), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("acted_by_user_id", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(["acted_by_user_id"], ["users.id"], name="fk_signatures_acted_by_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_signatures_document_id_documents", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_signatures_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("document_id", "founder_id", "version", name="pk_signatures"),
    )


def downgrade() -> None:
    op.drop_table("signatures")
    op.drop_table("document_versions")
    op.drop_table("site_builds")
    op.drop_table("messages")
    op.drop_table("memberships")
    op.drop_table("llm_usage")
    op.drop_table("jobs")
    op.drop_table("invites")
    op.drop_table("email_outbox")
    op.drop_table("documents")
    op.drop_table("checklist_items")
    op.drop_table("audit_log")
    op.drop_table("subscriptions")
    op.drop_table("sessions")
    op.drop_table("cases")
    op.drop_table("auth_tokens")
    op.drop_table("worker_heartbeats")
    op.drop_table("users")
    op.drop_table("rate_limits")
    op.drop_table("billing_events")
    op.drop_table("admin_audit")
