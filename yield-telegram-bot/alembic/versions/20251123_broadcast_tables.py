"""add broadcast tables

Revision ID: 20251123_broadcast_tables
Revises:
Create Date: 2025-11-23 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20251123_broadcast_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "telegram_users",
        sa.Column("is_subscribed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "telegram_users",
        sa.Column("tags", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
    )
    op.add_column(
        "telegram_users",
        sa.Column("last_active_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_telegram_users_language", "telegram_users", ["language"])
    op.create_index("ix_telegram_users_is_subscribed", "telegram_users", ["is_subscribed"])
    op.create_index("ix_telegram_users_last_active_at", "telegram_users", ["last_active_at"])

    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="operator"),
        sa.Column("api_key", sa.String(length=64), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_admin_users_email", "admin_users", ["email"], unique=True)

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=20), nullable=False, server_default="text"),
        sa.Column("content_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("filter_query", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("author_admin_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False, server_default="web_ui"),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("preview_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("total_recipients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("batch_size", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_broadcasts_status", "broadcasts", ["status"])
    op.create_index("ix_broadcasts_scheduled_at", "broadcasts", ["scheduled_at"])

    op.create_table(
        "broadcast_recipients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("broadcast_id", sa.Integer(), sa.ForeignKey("broadcasts.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("telegram_users.id"), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("language", sa.String(length=5), nullable=False, server_default="ua"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message_id", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("last_attempt_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recipients_broadcast_status", "broadcast_recipients", ["broadcast_id", "status"])

    op.create_table(
        "broadcast_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("broadcast_id", sa.Integer(), sa.ForeignKey("broadcasts.id"), nullable=False),
        sa.Column("admin_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("broadcast_events")
    op.drop_index("ix_recipients_broadcast_status", table_name="broadcast_recipients")
    op.drop_table("broadcast_recipients")
    op.drop_index("ix_broadcasts_scheduled_at", table_name="broadcasts")
    op.drop_index("ix_broadcasts_status", table_name="broadcasts")
    op.drop_table("broadcasts")
    op.drop_index("ix_admin_users_email", table_name="admin_users")
    op.drop_table("admin_users")
    op.drop_index("ix_telegram_users_last_active_at", table_name="telegram_users")
    op.drop_index("ix_telegram_users_is_subscribed", table_name="telegram_users")
    op.drop_index("ix_telegram_users_language", table_name="telegram_users")
    op.drop_column("telegram_users", "last_active_at")
    op.drop_column("telegram_users", "tags")
    op.drop_column("telegram_users", "is_subscribed")

