from pydantic import BaseModel, ConfigDict, Field


class PublicModerationDemoPayload(BaseModel):
    """Validates the short text accepted by the public moderation sandbox."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=800)
