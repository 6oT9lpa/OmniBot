"""add logging and moderation schema

Revision ID: 0002_add_logging_moderation_schema
Revises: 0001_initial_schema
Create Date: 2026-06-14 20:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0002_add_logging_moderation_schema"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_context().bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def add_column_if_missing(table_name: str, column: sa.Column, existing_type: str = None) -> None:
    if not has_column(table_name, column.name):
        op.add_column(table_name, column)


def create_table_if_missing(name: str, *args, **kwargs) -> None:
    inspector = inspect(op.get_context().bind)
    if not inspector.has_table(name):
        op.create_table(name, *args, **kwargs)


def upgrade() -> None:
    add_column_if_missing(
        "punishments",
        sa.Column("guild_id", sa.Integer(), nullable=True),
    )
    add_column_if_missing(
        "punishments",
        sa.Column("moderator_id", sa.Integer(), nullable=True),
    )
    add_column_if_missing(
        "punishments",
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
    )
    add_column_if_missing(
        "punishments",
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=True),
    )
    add_column_if_missing(
        "punishments",
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    add_column_if_missing(
        "punishments",
        sa.Column("retention_until", sa.DateTime(), nullable=True),
    )

    create_table_if_missing(
        "message_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("author_name", sa.Text(), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.datetime("now", "localtime"), nullable=False),
        sa.Column("retention_until", sa.DateTime()),
    )
    op.create_index("idx_message_logs_guild", "message_logs", ["guild_id"])
    op.create_index("idx_message_logs_event", "message_logs", ["event_type"])
    op.create_index("idx_message_logs_retention", "message_logs", ["retention_until"])

    create_table_if_missing(
        "guild_event_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer()),
        sa.Column("actor_id", sa.Integer()),
        sa.Column("actor_name", sa.Text()),
        sa.Column("target_id", sa.Integer()),
        sa.Column("target_name", sa.Text()),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("details", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.datetime("now", "localtime"), nullable=False),
        sa.Column("retention_until", sa.DateTime()),
    )
    op.create_index("idx_guild_event_logs_guild", "guild_event_logs", ["guild_id"])
    op.create_index("idx_guild_event_logs_event", "guild_event_logs", ["event_type"])
    op.create_index("idx_guild_event_logs_retention", "guild_event_logs", ["retention_until"])


def downgrade() -> None:
    op.drop_index("idx_guild_event_logs_retention", table_name="guild_event_logs")
    op.drop_index("idx_guild_event_logs_event", table_name="guild_event_logs")
    op.drop_index("idx_guild_event_logs_guild", table_name="guild_event_logs")
    op.drop_table("guild_event_logs")
    op.drop_index("idx_message_logs_retention", table_name="message_logs")
    op.drop_index("idx_message_logs_event", table_name="message_logs")
    op.drop_index("idx_message_logs_guild", table_name="message_logs")
    op.drop_table("message_logs")
