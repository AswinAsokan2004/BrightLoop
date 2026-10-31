"""Track customer-managed add-on lines and their change history.

Revision ID: 0003
Revises: 0002
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "subscription_lines", sa.Column("is_addon", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.create_table(
        "subscription_addon_changes",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column(
            "subscription_id",
            sa.Integer(),
            sa.ForeignKey("subscriptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("changed_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("before_items", postgresql.JSONB(), nullable=False),
        sa.Column("after_items", postgresql.JSONB(), nullable=False),
        sa.Column("before_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("after_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_subscription_addon_changes_subscription_id", "subscription_addon_changes", ["subscription_id"]
    )


def downgrade():
    op.drop_index("ix_subscription_addon_changes_subscription_id", table_name="subscription_addon_changes")
    op.drop_table("subscription_addon_changes")
    op.drop_column("subscription_lines", "is_addon")
