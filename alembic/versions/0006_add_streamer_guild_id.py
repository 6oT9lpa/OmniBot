"""Add guild_id to streamer alert sources.

Revision ID: 0006_add_streamer_guild_id
Revises: 0005_add_dev_blog_posts
Create Date: 2026-06-27 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_streamer_guild"
down_revision = "0005_dev_blog_posts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("streamers")}

    if "guild_id" not in columns:
        op.add_column(
            "streamers",
            sa.Column("guild_id", sa.BigInteger(), nullable=False, server_default="0"),
        )

    op.create_index("idx_streamers_guild", "streamers", ["guild_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("idx_streamers_guild", table_name="streamers", if_exists=True)
