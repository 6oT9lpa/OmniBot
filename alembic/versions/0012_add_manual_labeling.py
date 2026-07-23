"""add trusted guild labeling storage

Revision ID: 0012_manual_labeling
Revises: 0011_numeric_flags
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_manual_labeling"
down_revision = "0011_numeric_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("trusted_guilds", sa.Column("guild_id", sa.BigInteger(), primary_key=True), sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.create_table("labeling_roles", sa.Column("guild_id", sa.BigInteger(), nullable=False), sa.Column("user_id", sa.BigInteger(), nullable=False), sa.Column("role", sa.String(16), nullable=False), sa.Column("assigned_by", sa.BigInteger(), nullable=False), sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.PrimaryKeyConstraint("guild_id", "user_id", "role"))
    op.create_table("manual_labels", sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True), sa.Column("guild_id", sa.BigInteger(), nullable=False), sa.Column("channel_id", sa.BigInteger(), nullable=False), sa.Column("message_id", sa.BigInteger(), nullable=False), sa.Column("author_id", sa.BigInteger(), nullable=False), sa.Column("label", sa.String(64), nullable=False), sa.Column("comment", sa.Text()), sa.Column("content_snapshot", sa.Text()), sa.Column("source", sa.String(16), nullable=False, server_default="MANUAL"), sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"), sa.Column("labeled_by", sa.BigInteger(), nullable=False), sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"), sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.UniqueConstraint("guild_id", "message_id", "label", name="uq_manual_label"))
    op.create_table("labeling_audit", sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True), sa.Column("guild_id", sa.BigInteger(), nullable=False), sa.Column("actor_id", sa.BigInteger(), nullable=False), sa.Column("action", sa.String(64), nullable=False), sa.Column("target_id", sa.BigInteger()), sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.create_index("idx_manual_labels_guild_message", "manual_labels", ["guild_id", "message_id"])


def downgrade() -> None:
    op.drop_table("labeling_audit"); op.drop_table("manual_labels"); op.drop_table("labeling_roles"); op.drop_table("trusted_guilds")
