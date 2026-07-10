"""add server role purposes

Revision ID: 0004_add_server_role_purposes
Revises: 0003_add_role_panel_interaction_columns
Create Date: 2026-06-18 18:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0004_role_purposes"
down_revision: Union[str, None] = "0003_panel_interactions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def create_table_if_missing(name: str, *args, **kwargs) -> None:
    inspector = inspect(op.get_context().bind)
    if not inspector.has_table(name):
        op.create_table(name, *args, **kwargs)


def create_index_if_missing(name: str, table_name: str, columns: list[str]) -> None:
    inspector = inspect(op.get_context().bind)
    if not inspector.has_table(table_name):
        return
    if any(index.get("name") == name for index in inspector.get_indexes(table_name)):
        return
    op.create_index(name, table_name, columns)


def upgrade() -> None:
    create_table_if_missing(
        "server_role_purposes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("guild_id", "purpose", name="uq_server_role_purposes_guild_purpose"),
    )
    create_index_if_missing("idx_srp_guild", "server_role_purposes", ["guild_id"])
    create_index_if_missing("idx_srp_purpose", "server_role_purposes", ["purpose"])


def downgrade() -> None:
    op.drop_index("idx_srp_purpose", table_name="server_role_purposes")
    op.drop_index("idx_srp_guild", table_name="server_role_purposes")
    op.drop_table("server_role_purposes")
