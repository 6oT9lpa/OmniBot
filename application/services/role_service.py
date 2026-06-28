from typing import List, Optional, Dict, Any
import disnake
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from ipaddress import ip_address
from urllib.parse import urlparse

from core.interfaces.repositories import RoleRepositoryInterface
from core.interfaces.services import RoleServiceInterface
from infrastructure.config import BotConfig
from infrastructure.database.repositories.role_panel_message_repository import RolePanelMessageRepository
from infrastructure.database.repositories.role_panel_button_repository import RolePanelButtonRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)

MAX_PANEL_ITEMS = 25


def get_msk_timestamp() -> str:
    """Получить текущий timestamp в МСК"""
    msk_tz = timezone(timedelta(hours=3))
    return datetime.now(msk_tz).strftime("%Y-%m-%d %H:%M:%S")


class RoleService(RoleServiceInterface):
    def __init__(self, role_repo: RoleRepositoryInterface, config: BotConfig):
        self.role_repo = role_repo
        self.config = config
        self._bot: Optional[disnake.Client] = None
        self._panel_message_repo: Optional[RolePanelMessageRepository] = None
        self._panel_button_repo: Optional[RolePanelButtonRepository] = None

    def set_bot(self, bot: disnake.Client):
        self._bot = bot

    def set_panel_repositories(
        self,
        panel_message_repo: RolePanelMessageRepository,
        panel_button_repo: RolePanelButtonRepository,
    ):
        self._panel_message_repo = panel_message_repo
        self._panel_button_repo = panel_button_repo

    async def assign_auto_roles(self, member: disnake.Member) -> List[disnake.Role]:
        """Выдать автоматические роли новому участнику"""
        if not self._bot:
            logger.error("Bot not set in RoleService")
            return []

        auto_role_ids = await self.role_repo.get_auto_assign_roles()
        assigned = []

        for role_id in auto_role_ids:
            role = member.guild.get_role(role_id)
            if role:
                if member.guild.me.top_role.position > role.position:
                    try:
                        await member.add_roles(role, reason="Автовыдача при входе")
                        assigned.append(role)
                        logger.info("Assigned role id=%s to member id=%s", role_id, member.id)
                    except Exception as exc:
                        logger.error("Failed to assign role id=%s to member id=%s: %s", role_id, member.id, exc)
                else:
                    logger.warning("Cannot assign role id=%s to member id=%s: bot role is lower", role_id, member.id)

        return assigned

    async def sync_roles(self, guild: disnake.Guild) -> int:
        """Синхронизировать роли с Discord"""
        discord_roles = []

        for role in guild.roles:
            if role.is_default() or role.managed:
                continue
            discord_roles.append({
                "id": role.id,
                "name": role.name,
                "color": role.color.value,
                "position": role.position,
                "permissions": role.permissions.value,
                "managed": role.managed,
                "mentionable": role.mentionable,
            })

        synced_count = await self.role_repo.sync_from_discord(discord_roles)
        sync_activity_roles = getattr(self.role_repo, "sync_activity_roles_from_discord", None)
        if sync_activity_roles:
            await sync_activity_roles(guild.id, discord_roles)
        logger.info("Synced %s roles for guild id=%s", synced_count, guild.id)
        return synced_count

    async def get_all_roles(self) -> List[Dict[str, Any]]:
        return await self.role_repo.get_all_roles()

    async def get_public_roles(self) -> List[Dict[str, Any]]:
        return await self.role_repo.get_public_roles()

    async def get_role(self, role_id: int) -> Optional[Dict[str, Any]]:
        return await self.role_repo.get_role(role_id)

    async def set_auto_assign(self, role_id: int, is_auto_assign: bool) -> bool:
        return await self.role_repo.set_auto_assign(role_id, is_auto_assign)

    async def set_role_public(self, role_id: int, is_public: bool) -> bool:
        existing = await self.role_repo.get_role(role_id)
        if not existing:
            logger.warning("set_role_public: role id=%s not found in DB", role_id)
            return False
        await self.role_repo.set_public(role_id, is_public)
        logger.info("Role id=%s public set to %s", role_id, is_public)
        return True

    async def get_panels(self, guild_id: int) -> List[Dict[str, Any]]:
        if not self._panel_message_repo:
            raise ValueError("Panel message repository not set")
        return await self._panel_message_repo.get_by_guild(guild_id)

    async def get_panel(self, message_id: int) -> Optional[Dict[str, Any]]:
        if not self._panel_message_repo:
            raise ValueError("Panel message repository not set")
        return await self._panel_message_repo.get_by_message(message_id)

    async def create_role_panel(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        embed_title: str,
        embed_description: str,
        embed_color: int,
        created_by: int,
        interaction_mode: str = "buttons",
    ) -> int:
        if not self._panel_message_repo:
            raise ValueError("Panel message repository not set")
        return await self._panel_message_repo.create(
            guild_id,
            channel_id,
            message_id,
            embed_title,
            embed_description,
            embed_color,
            created_by,
            interaction_mode,
        )

    async def delete_panel(self, message_id: int) -> bool:
        if not self._panel_message_repo:
            raise ValueError("Panel message repository not set")
        panel = await self._panel_message_repo.get_by_message(message_id)
        if not panel:
            logger.warning("delete_panel: panel id=%s not found", message_id)
            return False
        return await self._panel_message_repo.delete_by_message(message_id)

    async def add_button_to_panel(
        self,
        message_id: int,
        role_id: int,
        role_name: str,
        emoji: str = None,
    ) -> bool:
        if not self._panel_button_repo or not self._panel_message_repo:
            raise ValueError("Panel repositories not set")

        panel = await self._panel_message_repo.get_by_message(message_id)
        if not panel:
            logger.warning("Panel not found for message id=%s", message_id)
            return False

        buttons = await self._panel_button_repo.get_all(panel["id"])
        if len(buttons) >= MAX_PANEL_ITEMS:
            raise ValueError(f"Panel cannot contain more than {MAX_PANEL_ITEMS} buttons or reactions")

        await self._panel_button_repo.add(panel["id"], role_id, role_name, emoji)
        await self.rebuild_panel_fingerprint(message_id)
        return True

    async def remove_button_from_panel(self, message_id: int, role_id: int) -> bool:
        if not self._panel_button_repo or not self._panel_message_repo:
            raise ValueError("Panel repositories not set")

        panel = await self._panel_message_repo.get_by_message(message_id)
        if not panel:
            return False

        result = await self._panel_button_repo.remove(panel["id"], role_id)
        if result:
            await self.rebuild_panel_fingerprint(message_id)
        return result

    async def get_panel_buttons(self, message_id: int) -> List[Dict[str, Any]]:
        if not self._panel_button_repo or not self._panel_message_repo:
            raise ValueError("Panel repositories not set")

        panel = await self._panel_message_repo.get_by_message(message_id)
        if not panel:
            return []

        return await self._panel_button_repo.get_all(panel["id"])

    async def rebuild_panel_fingerprint(self, message_id: int) -> None:
        if not self._panel_message_repo:
            raise ValueError("Panel message repository not set")

        buttons = await self.get_panel_buttons(message_id)
        fingerprint = self.calculate_buttons_fingerprint(buttons)
        await self._panel_message_repo.update_fingerprint(
            message_id,
            view_fingerprint=fingerprint,
        )

    async def ensure_panel_fingerprint(self, panel: Dict[str, Any]) -> Optional[str]:
        message_id = panel["message_id"]
        if panel.get("view_fingerprint"):
            return panel["view_fingerprint"]

        buttons = await self.get_panel_buttons(message_id)
        fingerprint = self.calculate_buttons_fingerprint(buttons)
        await self._update_panel_fingerprint(message_id, fingerprint)
        return fingerprint

    async def mark_panel_rendered(self, message_id: int, fingerprint: Optional[str]) -> None:
        if not self._panel_message_repo:
            raise ValueError("Panel message repository not set")
        await self._panel_message_repo.update_fingerprint(
            message_id,
            view_fingerprint=fingerprint,
            last_rendered_fingerprint=fingerprint,
        )

    async def refresh_panel_view(self, message_id: int, channel: disnake.TextChannel) -> bool:
        if not self._bot:
            return False

        try:
            panel = await self.get_panel(message_id)
            if not panel:
                return False

            fingerprint = await self.ensure_panel_fingerprint(panel)
            message = await channel.fetch_message(message_id)
            if not message:
                return False

            buttons = await self.get_panel_buttons(message_id)
            if not buttons:
                return False

            current_components = getattr(message, "components", None)
            if current_components and panel.get("last_rendered_fingerprint") == fingerprint:
                logger.debug("Skip unchanged panel render message_id=%s", message_id)
                return True

            from presentation.views.role_panel_view import RolePanelView
            from presentation.views.roles_panel_management.helpers import rebuild_panel_embed

            view = RolePanelView(buttons, message_id, self)
            panel_embed = await rebuild_panel_embed(self, channel.guild, panel, buttons)
            await message.edit(embed=panel_embed, view=view)
            await self.mark_panel_rendered(message_id, fingerprint)
            logger.info("Refreshed panel view for message id=%s", message_id)
            return True

        except Exception as exc:
            logger.error("Failed to refresh panel view message_id=%s: %s", message_id, exc)
            return False

    async def _update_panel_fingerprint(self, message_id: int, fingerprint: Optional[str]) -> None:
        if not self._panel_message_repo:
            raise ValueError("Panel message repository not set")
        await self._panel_message_repo.update_fingerprint(
            message_id,
            view_fingerprint=fingerprint,
        )

    @staticmethod
    def calculate_buttons_fingerprint(buttons: List[Dict[str, Any]]) -> Optional[str]:
        if not buttons:
            return None

        parts = []
        for button in sorted(buttons, key=lambda item: (item.get("position", 0), item.get("id", 0))):
            parts.append(f"{button['role_id']}:{button.get('emoji') or ''}")
        return sha256("|".join(parts).encode("utf-8")).hexdigest()

    @staticmethod
    def validate_image_url(url: Optional[str]) -> Optional[str]:
        if not url:
            return None

        parsed = urlparse(url.strip())
        if parsed.scheme.lower() != "https":
            raise ValueError("Only HTTPS image URLs are allowed")
        if not parsed.netloc:
            raise ValueError("Image URL must include a host")

        host = parsed.hostname
        if not host:
            raise ValueError("Image URL must include a host")

        try:
            ip = ip_address(host)
        except ValueError:
            return url.strip()

        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Private, loopback, link-local, and reserved IP addresses are not allowed")

        return url.strip()
