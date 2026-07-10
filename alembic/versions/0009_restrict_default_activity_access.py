"""restrict default Activity access to non-sensitive modules

Revision ID: 0009_restrict_default_activity_access
Revises: 0008_add_voice_room_members
Create Date: 2026-07-10 03:15:00
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


revision: str = "0009_restrict_activity"
down_revision: Union[str, None] = "0008_voice_members"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = inspect(op.get_context().bind)
    if not {
        "activity_access_roles",
        "activity_access_role_modules",
    }.issubset(inspector.get_table_names()):
        return

    # Before this revision the fallback User role received member directories,
    # voice-room metadata and server analytics automatically.  These values are
    # now opt-in through an explicitly assigned Activity role.
    op.execute(
        """
        DELETE FROM activity_access_role_modules AS modules
        USING activity_access_roles AS roles
        WHERE modules.access_role_id = roles.id
          AND roles.slug = 'user'
          AND modules.module_key IN ('integrations', 'server-stats', 'voice-rooms')
          AND modules.permission = 'view'
        """
    )


def downgrade() -> None:
    # The previous defaults intentionally are not restored: restoring them would
    # re-expose activity and membership metadata to every synced member.
    pass
