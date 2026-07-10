"""normalize existing PostgreSQL schemas for Discord snowflakes

Revision ID: 0010_postgresql_compatibility
Revises: 0009_restrict_default_activity_access
Create Date: 2026-07-10 04:10:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_postgres_compat"
down_revision: Union[str, None] = "0009_restrict_activity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_BIGINT_COLUMNS: dict[str, tuple[str, ...]] = {
    "messages": ("id", "guild_id", "channel_id", "author_id", "user_id", "reply_to_message_id"),
    "punishments": ("user_id", "mod_id", "guild_id", "moderator_id"),
    "streamers": ("user_id", "guild_id", "ping_role_id"),
    "server_stats": ("top_channel_id",),
    "roles": ("role_id", "guild_id"),
    "channel_config": ("channel_id", "guild_id"),
    "user_stats": ("user_id", "guild_id"),
    "role_panel_messages": ("guild_id", "channel_id", "message_id", "created_by"),
    "role_panel_buttons": ("panel_message_id", "role_id"),
    "message_logs": ("guild_id", "channel_id", "message_id", "author_id"),
    "guild_event_logs": ("guild_id", "channel_id", "actor_id", "target_id"),
    "server_channel_purposes": ("guild_id", "channel_id"),
    "welcome_config": ("guild_id", "rules_channel_id", "roles_channel_id"),
    "voice_rooms": ("channel_id", "guild_id", "owner_id", "admin_id"),
    "voice_room_members": ("channel_id", "guild_id", "user_id"),
    "voice_sessions": ("user_id", "guild_id", "channel_id"),
    "server_role_purposes": ("guild_id", "role_id"),
    "activity_synced_roles": ("guild_id", "role_id"),
    "activity_access_roles": ("guild_id",),
    "activity_synced_role_assignments": ("guild_id", "discord_role_id", "access_role_id"),
    "dev_blog_posts": ("guild_id", "channel_id", "message_id", "author_id"),
    "creator_alert_subscriptions": ("guild_id", "user_id", "ping_role_id"),
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("messages"):
        columns = {column["name"] for column in inspector.get_columns("messages")}
        if "author_id" in columns and "user_id" not in columns:
            op.alter_column("messages", "author_id", new_column_name="user_id")

    for table_name, column_names in _BIGINT_COLUMNS.items():
        if not inspector.has_table(table_name):
            continue
        columns = {column["name"]: column["type"] for column in inspector.get_columns(table_name)}
        for column_name in column_names:
            column_type = columns.get(column_name)
            if column_type is not None and not isinstance(column_type, sa.BigInteger):
                op.alter_column(table_name, column_name, type_=sa.BigInteger(), postgresql_using=f"{column_name}::bigint")

    if inspector.has_table("user_stats"):
        columns = {column["name"]: column["type"] for column in inspector.get_columns("user_stats")}
        if "last_message" in columns and not isinstance(columns["last_message"], sa.Text):
            op.alter_column("user_stats", "last_message", type_=sa.Text(), postgresql_using="last_message::text")
        if "created_at" not in columns:
            op.add_column("user_stats", sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")))
        if "updated_at" not in columns:
            op.add_column("user_stats", sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")))

    if inspector.has_table("streamers"):
        constraints = inspector.get_unique_constraints("streamers")
        legacy = next(
            (item for item in constraints if item.get("column_names") == ["user_id", "platform"]),
            None,
        )
        if legacy and legacy.get("name"):
            op.drop_constraint(legacy["name"], "streamers", type_="unique")
        if not any(item.get("column_names") == ["user_id", "guild_id", "platform"] for item in constraints):
            op.create_unique_constraint("uq_streamers_user_guild_platform", "streamers", ["user_id", "guild_id", "platform"])


def downgrade() -> None:
    # Narrowing Discord snowflakes back to 32-bit values risks data loss.
    pass
