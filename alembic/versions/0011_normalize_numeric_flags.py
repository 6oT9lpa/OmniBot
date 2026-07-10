"""normalize legacy PostgreSQL boolean flags to numeric values

Revision ID: 0011_numeric_flags
Revises: 0010_postgres_compat
Create Date: 2026-07-10 09:50:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_numeric_flags"
down_revision: Union[str, None] = "0010_postgres_compat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FLAG_COLUMNS: dict[str, dict[str, int]] = {
    "messages": {"deleted": 0, "edited": 0, "ai_flagged": 0},
    "punishments": {"active": 1, "is_active": 1},
    "streamers": {"active": 1},
    "roles": {"is_auto_assign": 0, "is_public": 1},
    "channel_config": {"is_ai_whitelisted": 0, "welcome_enabled": 1},
    "role_panel_messages": {"is_active": 1},
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name, columns in _FLAG_COLUMNS.items():
        if not inspector.has_table(table_name):
            continue
        current_columns = {column["name"]: column["type"] for column in inspector.get_columns(table_name)}
        for column_name, default in columns.items():
            if not isinstance(current_columns.get(column_name), sa.Boolean):
                continue
            op.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" DROP DEFAULT')
            op.alter_column(
                table_name,
                column_name,
                type_=sa.BigInteger(),
                postgresql_using=(
                    f'CASE WHEN "{column_name}" IS TRUE THEN 1 '
                    f'WHEN "{column_name}" IS FALSE THEN 0 ELSE NULL END'
                ),
            )
            op.alter_column(table_name, column_name, server_default=sa.text(str(default)))


def downgrade() -> None:
    # Numeric flags are the application-level storage format; narrowing them
    # back to booleans would not preserve arbitrary legacy numeric values.
    pass
