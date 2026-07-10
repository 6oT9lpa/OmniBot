"""add voice room admin id

Revision ID: 0007_add_voice_room_admin_id
Revises: 0006_add_streamer_guild_id
Create Date: 2026-06-29 20:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0007_voice_admin"
down_revision: Union[str, None] = "0006_streamer_guild"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = inspect(op.get_context().bind)
    if not inspector.has_table("voice_rooms"):
        return

    columns = {column["name"] for column in inspector.get_columns("voice_rooms")}
    if "admin_id" not in columns:
        op.add_column("voice_rooms", sa.Column("admin_id", sa.BigInteger(), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("voice_rooms")}
    if "idx_voice_rooms_admin" not in indexes:
        op.create_index("idx_voice_rooms_admin", "voice_rooms", ["admin_id"])


def downgrade() -> None:
    inspector = inspect(op.get_context().bind)
    if not inspector.has_table("voice_rooms"):
        return

    indexes = {index["name"] for index in inspector.get_indexes("voice_rooms")}
    if "idx_voice_rooms_admin" in indexes:
        op.drop_index("idx_voice_rooms_admin", table_name="voice_rooms")

    columns = {column["name"] for column in inspector.get_columns("voice_rooms")}
    if "admin_id" in columns:
        op.drop_column("voice_rooms", "admin_id")
