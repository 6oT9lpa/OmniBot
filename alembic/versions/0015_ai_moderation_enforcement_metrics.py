"""add AI moderation enforcement audit fields

Revision ID: 0015_ai_enforcement_metrics
Revises: 0014_member_join_history
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_ai_enforcement_metrics"
down_revision = "0014_member_join_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_moderation_events", sa.Column("proposed_action", sa.String(32), nullable=True))
    op.add_column("ai_moderation_events", sa.Column("confidence", sa.Float(), nullable=False, server_default="0"))
    op.add_column("ai_moderation_events", sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"))
    op.create_table("ai_moderation_metrics_access", sa.Column("guild_id", sa.BigInteger(), primary_key=True), sa.Column("granted_by", sa.BigInteger(), nullable=False), sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))


def downgrade() -> None:
    op.drop_table("ai_moderation_metrics_access")
    op.drop_column("ai_moderation_events", "latency_ms")
    op.drop_column("ai_moderation_events", "confidence")
    op.drop_column("ai_moderation_events", "proposed_action")
