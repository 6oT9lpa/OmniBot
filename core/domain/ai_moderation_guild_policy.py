from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.domain.ai_moderation_action import AiModerationAction
from core.domain.ai_moderation_label_policy import AiModerationLabelPolicy


class AiModerationGuildPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    blacklist_words: tuple[str, ...] = Field(default=(), max_length=200)
    allowed_domains: tuple[str, ...] = Field(default=(), max_length=200)
    labels: dict[str, AiModerationLabelPolicy] = Field(default_factory=dict, max_length=32)
    blacklist_action: AiModerationAction = AiModerationAction.DELETE_WARN
    unapproved_domain_action: AiModerationAction = AiModerationAction.REVIEW

    @field_validator("blacklist_words", "allowed_domains")
    @classmethod
    def normalize_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(value.strip().casefold() for value in values if value.strip()))
        if any(len(value) > 253 for value in normalized):
            raise ValueError("policy value exceeds maximum length")
        return normalized

    @field_validator("labels", mode="before")
    @classmethod
    def normalize_labels(cls, values: Mapping[str, object]) -> dict[str, object]:
        if not isinstance(values, Mapping):
            raise ValueError("labels must be an object")
        return {str(label).strip().upper(): value for label, value in values.items() if str(label).strip()}
