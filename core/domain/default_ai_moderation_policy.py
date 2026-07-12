from core.domain.ai_moderation_action import AiModerationAction
from core.domain.ai_moderation_guild_policy import AiModerationGuildPolicy
from core.domain.ai_moderation_label_policy import AiModerationLabelPolicy


def default_ai_moderation_policy() -> AiModerationGuildPolicy:
    return AiModerationGuildPolicy(
        labels={
            "SPAM": AiModerationLabelPolicy(risk_threshold=30, max_action=AiModerationAction.DELETE),
            "ADVERTISEMENT": AiModerationLabelPolicy(risk_threshold=25, max_action=AiModerationAction.DELETE),
            "INVITE": AiModerationLabelPolicy(risk_threshold=20, max_action=AiModerationAction.DELETE),
            "SCAM": AiModerationLabelPolicy(
                risk_threshold=55,
                min_action=AiModerationAction.DELETE_WARN,
                max_action=AiModerationAction.BAN,
            ),
            "TOXIC": AiModerationLabelPolicy(risk_threshold=45, max_action=AiModerationAction.WARN),
            "PROFANITY": AiModerationLabelPolicy(risk_threshold=25, max_action=AiModerationAction.WARN),
            "POLITICS_IRL": AiModerationLabelPolicy(
                risk_threshold=40,
                min_action=AiModerationAction.REVIEW,
                max_action=AiModerationAction.REVIEW,
            ),
            "HATE": AiModerationLabelPolicy(
                risk_threshold=55,
                min_action=AiModerationAction.WARN,
                max_action=AiModerationAction.TIMEOUT,
            ),
            "THREAT": AiModerationLabelPolicy(
                risk_threshold=65,
                min_action=AiModerationAction.DELETE_WARN,
                max_action=AiModerationAction.BAN,
            ),
            "NSFW": AiModerationLabelPolicy(
                risk_threshold=55,
                min_action=AiModerationAction.DELETE,
                max_action=AiModerationAction.TIMEOUT,
            ),
            "EVASION": AiModerationLabelPolicy(
                risk_threshold=50,
                min_action=AiModerationAction.WARN,
                max_action=AiModerationAction.TIMEOUT,
            ),
            "FLOOD": AiModerationLabelPolicy(risk_threshold=30, max_action=AiModerationAction.DELETE),
            "URL": AiModerationLabelPolicy(
                risk_threshold=45,
                min_action=AiModerationAction.REVIEW,
                max_action=AiModerationAction.DELETE,
            ),
            "IMAGE_SCAM": AiModerationLabelPolicy(
                risk_threshold=55,
                min_action=AiModerationAction.DELETE_WARN,
                max_action=AiModerationAction.BAN,
            ),
        }
    )
