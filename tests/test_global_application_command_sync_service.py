from types import SimpleNamespace

import pytest

from application.services.global_application_command_sync_service import GlobalApplicationCommandSyncService


@pytest.mark.asyncio
async def test_global_command_sync_uses_atomic_bulk_overwrite() -> None:
    command_bodies = [
        SimpleNamespace(name="set", type="chat_input"),
        SimpleNamespace(name="list", type="chat_input"),
        SimpleNamespace(name="ai-policy", type="chat_input"),
    ]
    bot = _Bot(command_bodies)

    commands = await GlobalApplicationCommandSyncService().sync_global_commands(bot)

    assert commands == command_bodies
    assert bot.bulk_overwrite_calls == [command_bodies]


class _Bot:
    def __init__(self, command_bodies: list[SimpleNamespace]) -> None:
        self.application_id = 1
        self._commands = [SimpleNamespace(body=command) for command in command_bodies]
        self.bulk_overwrite_calls: list[list[SimpleNamespace]] = []

    def application_commands_iterator(self):
        return iter(self._commands)

    async def bulk_overwrite_global_commands(self, commands: list[SimpleNamespace]) -> None:
        self.bulk_overwrite_calls.append(commands)
