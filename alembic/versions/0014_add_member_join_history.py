"""add member join history

Revision ID: 0014_member_join_history
Revises: 0013_punishment_event_identity
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_member_join_history"
down_revision = "0013_punishment_event_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "member_join_history",
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("first_joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("join_count", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("guild_id", "user_id"),
    )
    op.create_index("idx_member_join_history_latest", "member_join_history", ["guild_id", "latest_joined_at"])


def downgrade() -> None:
    op.drop_index("idx_member_join_history_latest", table_name="member_join_history")
    op.drop_table("member_join_history")
