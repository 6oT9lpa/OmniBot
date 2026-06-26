"""add dev blog posts

Revision ID: 0005_add_dev_blog_posts
Revises: 0004_add_server_role_purposes
Create Date: 2026-06-27 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0005_add_dev_blog_posts"
down_revision: Union[str, None] = "0004_add_server_role_purposes"
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
        "dev_blog_posts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="published"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.datetime("now", "localtime")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.datetime("now", "localtime")),
    )
    create_index_if_missing("idx_dev_blog_posts_guild", "dev_blog_posts", ["guild_id"])
    create_index_if_missing("idx_dev_blog_posts_author", "dev_blog_posts", ["author_id"])


def downgrade() -> None:
    op.drop_index("idx_dev_blog_posts_author", table_name="dev_blog_posts")
    op.drop_index("idx_dev_blog_posts_guild", table_name="dev_blog_posts")
    op.drop_table("dev_blog_posts")
