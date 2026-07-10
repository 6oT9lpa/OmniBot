"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-14 20:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
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
    existing_indexes = inspector.get_indexes(table_name)
    if any(index.get("name") == name for index in existing_indexes):
        return
    op.create_index(name, table_name, columns)


def upgrade() -> None:
    create_table_if_missing(
        "messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("deleted", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("edited", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("edited_content", sa.Text()),
        sa.Column("ai_flagged", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("ai_reason", sa.Text()),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    create_index_if_missing("idx_messages_user", "messages", ["user_id"])
    create_index_if_missing("idx_messages_channel", "messages", ["channel_id"])
    create_index_if_missing("idx_messages_timestamp", "messages", ["timestamp"])
    create_index_if_missing("idx_messages_deleted", "messages", ["deleted"])

    create_table_if_missing(
        "punishments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("mod_id", sa.BigInteger()),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("duration", sa.Text()),
        sa.Column("expires_at", sa.DateTime()),
        sa.Column("active", sa.BigInteger(), server_default="1", nullable=False),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    create_index_if_missing("idx_punishments_user", "punishments", ["user_id"])
    create_index_if_missing("idx_punishments_active", "punishments", ["active"])
    create_index_if_missing("idx_punishments_expires", "punishments", ["expires_at"])

    create_table_if_missing(
        "streamers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("channel_url", sa.Text(), nullable=False),
        sa.Column("channel_name", sa.Text()),
        sa.Column("template", sa.Text()),
        sa.Column("ping_role_id", sa.BigInteger()),
        sa.Column("active", sa.BigInteger(), server_default="1", nullable=False),
        sa.Column("last_stream_id", sa.Text()),
        sa.Column("last_check", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("platform IN ('twitch', 'youtube', 'kick')", name="ck_streamers_platform"),
        sa.UniqueConstraint("user_id", "platform", name="uq_streamers_user_platform"),
    )
    create_index_if_missing("idx_streamers_user", "streamers", ["user_id"])
    create_index_if_missing("idx_streamers_platform", "streamers", ["platform"])
    create_index_if_missing("idx_streamers_active", "streamers", ["active"])

    create_table_if_missing(
        "server_stats",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("date", sa.Text(), unique=True),
        sa.Column("members_total", sa.BigInteger(), server_default="0"),
        sa.Column("members_online", sa.BigInteger(), server_default="0"),
        sa.Column("members_voice", sa.BigInteger(), server_default="0"),
        sa.Column("messages_count", sa.BigInteger(), server_default="0"),
        sa.Column("voice_hours", sa.REAL(), server_default="0"),
        sa.Column("new_members", sa.BigInteger(), server_default="0"),
        sa.Column("left_members", sa.BigInteger(), server_default="0"),
        sa.Column("top_channel_id", sa.BigInteger()),
        sa.Column("top_channel_count", sa.BigInteger()),
    )
    create_index_if_missing("idx_stats_date", "server_stats", ["date"])

    create_table_if_missing(
        "roles",
        sa.Column("role_id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("color", sa.BigInteger()),
        sa.Column("position", sa.BigInteger()),
        sa.Column("is_auto_assign", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("is_public", sa.BigInteger(), server_default="1", nullable=False),
        sa.Column("display_emoji", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    create_index_if_missing("idx_roles_guild", "roles", ["guild_id"])
    create_index_if_missing("idx_roles_auto_assign", "roles", ["is_auto_assign"])

    create_table_if_missing(
        "channel_config",
        sa.Column("channel_id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("is_ai_whitelisted", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("welcome_enabled", sa.BigInteger(), server_default="1", nullable=False),
        sa.Column("slowmode_override", sa.BigInteger()),
        sa.Column("auto_delete_after", sa.BigInteger()),
        sa.Column("custom_name", sa.Text()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    create_index_if_missing("idx_channel_guild", "channel_config", ["guild_id"])
    create_index_if_missing("idx_channel_whitelist", "channel_config", ["is_ai_whitelisted"])

    create_table_if_missing(
        "user_stats",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("messages_count", sa.BigInteger(), server_default="0"),
        sa.Column("voice_minutes", sa.BigInteger(), server_default="0"),
        sa.Column("warnings_count", sa.BigInteger(), server_default="0"),
        sa.Column("last_message", sa.Text()),
        sa.Column("joined_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("user_id", "guild_id"),
    )
    create_index_if_missing("idx_user_stats_messages", "user_stats", ["messages_count"])

    create_table_if_missing(
        "role_panel_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("embed_title", sa.Text(), server_default="Выберите свою роль"),
        sa.Column("embed_description", sa.Text(), server_default="Нажмите на кнопку, чтобы получить или снять роль"),
        sa.Column("embed_color", sa.BigInteger(), server_default="65280"),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("is_active", sa.BigInteger(), server_default="1", nullable=False),
        sa.Column("interaction_mode", sa.Text(), server_default="buttons", nullable=False),
        sa.Column("view_fingerprint", sa.Text()),
        sa.Column("last_rendered_fingerprint", sa.Text()),
        sa.UniqueConstraint("guild_id", "channel_id", "message_id", name="uq_role_panel_messages_location"),
    )
    create_index_if_missing("idx_role_panel_messages_guild", "role_panel_messages", ["guild_id"])
    create_index_if_missing("idx_role_panel_messages_active", "role_panel_messages", ["is_active"])

    create_table_if_missing(
        "role_panel_buttons",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("panel_message_id", sa.BigInteger(), sa.ForeignKey("role_panel_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("role_name", sa.Text(), nullable=False),
        sa.Column("emoji", sa.Text()),
        sa.Column("position", sa.BigInteger(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("panel_message_id", "role_id", name="uq_role_panel_buttons_panel_role"),
    )
    create_index_if_missing("idx_role_panel_buttons_panel", "role_panel_buttons", ["panel_message_id"])

    create_table_if_missing(
        "server_channel_purposes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("guild_id", "purpose", name="uq_server_channel_purposes_guild_purpose"),
    )
    create_index_if_missing("idx_scp_guild", "server_channel_purposes", ["guild_id"])
    create_index_if_missing("idx_scp_purpose", "server_channel_purposes", ["purpose"])

    create_table_if_missing(
        "welcome_config",
        sa.Column("guild_id", sa.BigInteger(), primary_key=True),
        sa.Column("title", sa.Text(), server_default="Добро пожаловать!"),
        sa.Column("description", sa.Text()),
        sa.Column("thumbnail_url", sa.Text()),
        sa.Column("footer_text", sa.Text()),
        sa.Column("footer_icon_url", sa.Text()),
        sa.Column("color", sa.BigInteger(), server_default="5763719"),
        sa.Column("is_enabled", sa.BigInteger(), server_default="1"),
        sa.Column("rules_channel_id", sa.BigInteger()),
        sa.Column("roles_channel_id", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("welcome_config")
    op.drop_index("idx_scp_purpose", table_name="server_channel_purposes")
    op.drop_index("idx_scp_guild", table_name="server_channel_purposes")
    op.drop_table("server_channel_purposes")
    op.drop_index("idx_role_panel_buttons_panel", table_name="role_panel_buttons")
    op.drop_table("role_panel_buttons")
    op.drop_index("idx_role_panel_messages_active", table_name="role_panel_messages")
    op.drop_index("idx_role_panel_messages_guild", table_name="role_panel_messages")
    op.drop_table("role_panel_messages")
    op.drop_index("idx_user_stats_messages", table_name="user_stats")
    op.drop_table("user_stats")
    op.drop_index("idx_channel_whitelist", table_name="channel_config")
    op.drop_index("idx_channel_guild", table_name="channel_config")
    op.drop_table("channel_config")
    op.drop_index("idx_roles_auto_assign", table_name="roles")
    op.drop_index("idx_roles_guild", table_name="roles")
    op.drop_table("roles")
    op.drop_index("idx_stats_date", table_name="server_stats")
    op.drop_table("server_stats")
    op.drop_index("idx_streamers_active", table_name="streamers")
    op.drop_index("idx_streamers_platform", table_name="streamers")
    op.drop_index("idx_streamers_user", table_name="streamers")
    op.drop_table("streamers")
    op.drop_index("idx_punishments_expires", table_name="punishments")
    op.drop_index("idx_punishments_active", table_name="punishments")
    op.drop_index("idx_punishments_user", table_name="punishments")
    op.drop_table("punishments")
    op.drop_index("idx_messages_deleted", table_name="messages")
    op.drop_index("idx_messages_timestamp", table_name="messages")
    op.drop_index("idx_messages_channel", table_name="messages")
    op.drop_index("idx_messages_author", table_name="messages")
    op.drop_table("messages")

