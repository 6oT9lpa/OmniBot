"""add event identity to punishment records

Revision ID: 0013_punishment_event_identity
Revises: 0012_manual_labeling
"""

from alembic import op
import sqlalchemy as sa

revision = "0013_punishment_event_identity"
down_revision = "0012_manual_labeling"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("punishments", sa.Column("message_id", sa.BigInteger(), nullable=True))
    op.add_column("punishments", sa.Column("source", sa.String(16), nullable=False, server_default="HUMAN"))
    op.create_unique_constraint(
        "uq_punishments_event_identity",
        "punishments",
        ["guild_id", "message_id", "type", "source"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_punishments_event_identity", "punishments", type_="unique")
    op.drop_column("punishments", "source")
    op.drop_column("punishments", "message_id")
