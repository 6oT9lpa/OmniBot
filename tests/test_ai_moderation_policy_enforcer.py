from datetime import datetime, timezone

import pytest

from application.dto.ai_moderation_decision import AiModerationDecision
from application.dto.ai_moderation_request import AiModerationRequest
from application.services.ai_moderation_policy_enforcer import AiModerationPolicyEnforcer


def test_policy_enforcer_clamps_label_action_and_respects_risk_threshold() -> None:
    enforcer = AiModerationPolicyEnforcer()
    request = _request("ordinary message")
    decision = _decision(action="BAN", risk_score=40, labels=("TOXIC",))

    adjusted = enforcer.apply(
        request,
        decision,
        {"labels": {"TOXIC": {"risk_threshold": 45, "min_action": "LOG", "max_action": "WARN"}}},
    )

    assert adjusted.action == "LOG"
    assert adjusted.execution_plan == ("LOG",)


def test_policy_enforcer_blacklist_overrides_safe_ai_decision() -> None:
    enforcer = AiModerationPolicyEnforcer()
    adjusted = enforcer.apply(
        _request("contains forbidden-term here"),
        _decision(action="IGNORE", risk_score=0, labels=("SAFE",)),
        {"blacklist_words": ["forbidden-term"]},
    )

    assert adjusted.action == "DELETE_WARN"
    assert adjusted.execution_plan == ("DELETE", "WARN")
    assert adjusted.primary_label == "BLACKLIST"


def test_policy_enforcer_reviews_unapproved_domain() -> None:
    enforcer = AiModerationPolicyEnforcer()
    adjusted = enforcer.apply(
        _request("visit https://untrusted.example/path"),
        _decision(action="IGNORE", risk_score=0, labels=("SAFE",)),
        {"allowed_domains": ["discord.com"]},
    )

    assert adjusted.action == "REVIEW"


def test_policy_enforcer_rejects_inverted_action_range() -> None:
    enforcer = AiModerationPolicyEnforcer()

    with pytest.raises(ValueError, match="min_action"):
        enforcer.validate({"labels": {"TOXIC": {"min_action": "BAN", "max_action": "LOG"}}})


def _request(raw_text: str) -> AiModerationRequest:
    return AiModerationRequest(
        guild_id=1,
        channel_id=2,
        user_id=3,
        message_id=4,
        raw_text=raw_text,
        created_at=datetime.now(timezone.utc),
    )


def _decision(action: str, risk_score: float, labels: tuple[str, ...]) -> AiModerationDecision:
    return AiModerationDecision(
        event_id=1,
        user_id=3,
        guild_id=1,
        message_id=4,
        risk_score=risk_score,
        action=action,
        primary_label=labels[0],
        labels=labels,
        execution_plan=(action,),
        dry_run=False,
    )
