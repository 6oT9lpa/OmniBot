from core.domain.ai_moderation_guild_policy import AiModerationGuildPolicy
from core.domain.default_ai_moderation_policy import default_ai_moderation_policy, merge_with_default_ai_moderation_policy


def test_default_ai_moderation_policy_covers_moderated_labels() -> None:
    policy = default_ai_moderation_policy()

    assert policy.labels["TOXIC"].risk_threshold == 45
    assert policy.labels["PROFANITY"].max_action == "WARN"
    assert policy.labels["POLITICS_IRL"].min_action == "REVIEW"
    assert policy.labels["POLITICS_IRL"].max_action == "REVIEW"
    assert policy.labels["SCAM"].min_action == "DELETE_WARN"
    assert policy.labels["THREAT"].max_action == "BAN"
    assert policy.blacklist_words == ()
    assert policy.allowed_domains == ()


def test_default_policy_is_merged_into_existing_guild_policy() -> None:
    policy = merge_with_default_ai_moderation_policy(
        AiModerationGuildPolicy.model_validate({"labels": {"TOXIC": {"risk_threshold": 60, "min_action": "WARN", "max_action": "TIMEOUT"}}})
    )

    assert policy.labels["TOXIC"].risk_threshold == 60
    assert policy.labels["PROFANITY"].max_action == "WARN"
    assert policy.labels["POLITICS_IRL"].min_action == "REVIEW"
