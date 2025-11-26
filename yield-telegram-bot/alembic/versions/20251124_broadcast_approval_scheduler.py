"""add approval fields to broadcasts

Revision ID: 20251124_broadcast_approval_scheduler
Revises: 20251123_broadcast_tables
Create Date: 2025-11-24 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20251124_broadcast_approval_scheduler"
down_revision = "20251123_broadcast_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "broadcasts",
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "broadcasts",
        sa.Column("approved_by_admin_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("broadcasts", "approved_by_admin_id")
    op.drop_column("broadcasts", "approved_at")


