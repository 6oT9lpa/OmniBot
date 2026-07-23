class LabelingPermissionService:
    def __init__(self, repository, owner_id: int | None) -> None:
        self._repository = repository
        self._owner_id = owner_id

    async def is_owner(self, actor_id: int) -> bool:
        return actor_id == self._owner_id

    async def can_manage(self, actor_id: int, guild_id: int) -> bool:
        return await self.is_owner(actor_id) or await self._repository.has_role(guild_id, actor_id, "ADMIN")

    async def can_label(self, actor_id: int, guild_id: int) -> bool:
        return await self._repository.is_trusted(guild_id) and (await self.can_manage(actor_id, guild_id) or await self._repository.has_role(guild_id, actor_id, "LABELER"))
