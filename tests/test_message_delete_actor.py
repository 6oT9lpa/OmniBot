import pytest

from presentation.cogs.logging_cog import LoggingCog


class _User:
    def __init__(self, user_id: int):
        self.id = user_id
        self.bot = False


class _Guild:
    async def audit_logs(self, **_kwargs):
        if False:
            yield None


class _Message:
    def __init__(self, message_id: int, author: _User):
        self.id = message_id
        self.author = author
        self.guild = _Guild()


class _LoggingService:
    def __init__(self):
        self.deleted_by = None

    async def log_message_delete(self, _message, *, deleted_by):
        self.deleted_by = deleted_by


class _Bot:
    def __init__(self, user):
        self.user = user


@pytest.mark.asyncio
async def test_ai_delete_is_attributed_to_omnibot() -> None:
    bot_user = _User(100)
    service = _LoggingService()
    cog = LoggingCog(_Bot(bot_user), service, None, None)
    cog.register_bot_message_deletion(50)

    await cog.on_message_delete(_Message(50, _User(200)))

    assert service.deleted_by is bot_user


@pytest.mark.asyncio
async def test_self_delete_is_attributed_to_message_author() -> None:
    service = _LoggingService()
    author = _User(200)
    cog = LoggingCog(_Bot(_User(100)), service, None, None)

    await cog.on_message_delete(_Message(50, author))

    assert service.deleted_by is author
