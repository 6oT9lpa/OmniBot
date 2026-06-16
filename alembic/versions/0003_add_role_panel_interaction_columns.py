"""add role panel interaction columns

Revision ID: 0003_add_role_panel_interaction_columns
Revises: 0002_add_logging_moderation_schema
Create Date: 2026-06-14 20:45:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0003_add_role_panel_interaction_columns"
down_revision: Union[str, None] = "0002_add_logging_moderation_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_context().bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not has_column(table_name, column.name):
        op.add_column(table_name, column)


def create_index_if_missing(name: str, table_name: str, columns: list[str]) -> None:
    inspector = inspect(op.get_context().bind)
    if not inspector.has_table(table_name):
        return
    if any(index.get("name") == name for index in inspector.get_indexes(table_name)):
        return
    op.create_index(name, table_name, columns)


def upgrade() -> None:
    add_column_if_missing(
        "role_panel_messages",
        sa.Column("interaction_mode", sa.Text(), nullable=True),
    )
    add_column_if_missing(
        "role_panel_messages",
        sa.Column("view_fingerprint", sa.Text(), nullable=True),
    )
    add_column_if_missing(
        "role_panel_messages",
        sa.Column("last_rendered_fingerprint", sa.Text(), nullable=True),
    )
    create_index_if_missing("idx_role_panel_messages_mode", "role_panel_messages", ["interaction_mode"])


def downgrade() -> None:
    pass
