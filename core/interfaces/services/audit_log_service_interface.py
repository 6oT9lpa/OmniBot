from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import disnake


class AuditLogServiceInterface(ABC):
    @abstractmethod
    async def send_to_log_channel(
        self,
        guild_id: int,
        embed: disnake.Embed,
        *,
        channel_id: Optional[int] = None,
        event_type: Optional[str] = None,
    ) -> None:
        pass

    @abstractmethod
    async def get_log_channel(
        self,
        guild_id: int,
        event_type: Optional[str] = None,
        channel_id: Optional[int] = None,
    ) -> Optional[disnake.TextChannel]:
        pass

    @abstractmethod
    async def setup_log_channels(
        self,
        guild: disnake.Guild,
        logs_channel_id: int,
        deleted_messages_channel_id: Optional[int] = None,
    ) -> bool:
        pass
