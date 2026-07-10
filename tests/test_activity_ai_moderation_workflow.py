import pytest
import pytest_asyncio

import activity.server.dependencies as activity_dependencies
import activity.server.services.ai_moderation_service as ai_service_module
from activity.server.schemas.ai_moderation_channels import AiModerationChannelsPayload
from activity.server.schemas.ai_moderation_policy import AiModerationPolicyPayload
from activity.server.services.ai_moderation_service import AiModerationService


@pytest_asyncio.fixture
async def activity_ai_db(postgres_test_db):
    previous_db = activity_dependencies._db
    activity_dependencies._db = postgres_test_db
    try:
        yield postgres_test_db
    finally:
        activity_dependencies._db = previous_db


@pytest.mark.asyncio
async def test_ai_moderation_persists_exact_discord_snowflakes_and_policy(activity_ai_db, monkeypatch):
    """This covers the Activity save-and-reload workflow with production-size Discord IDs."""
    service = AiModerationService()
    guild_id = 1515345326909952052
    selected_channel_id = 1515345606816694403
    rejected_channel_id = 1515345606816694404
    validated_channel_sets: list[set[int]] = []

    async def ensure_access(*_):
        return {"id": "42", "username": "admin"}, {"is_admin": True}

    async def filter_channels(received_guild_id: str, channel_ids: set[int]):
        assert received_guild_id == str(guild_id)
        validated_channel_sets.append(channel_ids)
        return {selected_channel_id}

    async def list_channels(*_):
        return []

    monkeypatch.setattr(service._access_service, "ensure_module_access", ensure_access)
    monkeypatch.setattr(service._discord_service, "filter_moderation_channel_ids", filter_channels)
    monkeypatch.setattr(service._discord_service, "list_channels", list_channels)
    monkeypatch.setattr(ai_service_module, "get_db", lambda: activity_ai_db)

    # Pydantic accepts decimal strings without changing their value before database storage.
    channels_payload = AiModerationChannelsPayload(
        guild_id=str(guild_id),
        channel_ids=[str(selected_channel_id), str(rejected_channel_id)],
    )
    saved_channels = await service.save_channels(channels_payload, "token")

    policy_payload = AiModerationPolicyPayload(
        guild_id=str(guild_id),
        policy={
            "blacklist_words": ["Fraud", "fraud", "spam"],
            "allowed_domains": ["Example.COM"],
            "labels": {},
            "blacklist_action": "DELETE_WARN",
            "unapproved_domain_action": "REVIEW",
        },
    )
    saved_policy = await service.save_policy(policy_payload, "token")

    reloaded = await service.get_settings(guild_id, "token")

    assert validated_channel_sets == [{selected_channel_id, rejected_channel_id}]
    assert saved_channels["channels"] == [str(selected_channel_id)]
    assert saved_policy["policy"]["blacklist_words"] == ["fraud", "spam"]
    assert reloaded["channels"] == [str(selected_channel_id)]
    assert reloaded["policy"]["allowed_domains"] == ["example.com"]
