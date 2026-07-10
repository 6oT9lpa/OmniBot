"""add voice room members

Revision ID: 0008_add_voice_room_members
Revises: 0007_add_voice_room_admin_id
Create Date: 2026-06-29 22:15:00
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

revision: str = "0008_voice_members"
down_revision: Union[str, None] = "0007_voice_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = inspect(op.get_context().bind)
    if not inspector.has_table("voice_room_members"):
        op.execute(
            """
            CREATE TABLE voice_room_members (
                channel_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel_id, user_id)
            )
            """
        )

    indexes = {index["name"] for index in inspector.get_indexes("voice_room_members")}
    if "idx_voice_room_members_guild" not in indexes:
        op.create_index("idx_voice_room_members_guild", "voice_room_members", ["guild_id"])
    if "idx_voice_room_members_user" not in indexes:
        op.create_index("idx_voice_room_members_user", "voice_room_members", ["user_id"])


def downgrade() -> None:
    inspector = inspect(op.get_context().bind)
    if inspector.has_table("voice_room_members"):
        op.drop_table("voice_room_members")
