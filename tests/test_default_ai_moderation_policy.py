from core.domain.default_ai_moderation_policy import default_ai_moderation_policy


def test_default_ai_moderation_policy_covers_moderated_labels() -> None:
    policy = default_ai_moderation_policy()

    assert policy.labels["TOXIC"].risk_threshold == 45
    assert policy.labels["SCAM"].min_action == "DELETE_WARN"
    assert policy.labels["THREAT"].max_action == "BAN"
    assert policy.blacklist_words == ()
    assert policy.allowed_domains == ()
