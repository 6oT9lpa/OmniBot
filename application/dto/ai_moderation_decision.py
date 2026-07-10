from pydantic import BaseModel, ConfigDict, Field


class AiModerationDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    guild_id: int = Field(gt=0)
    message_id: int = Field(gt=0)
    risk_score: float = Field(ge=0, le=100)
    action: str = Field(min_length=1, max_length=32)
    primary_label: str = Field(min_length=1, max_length=32)
    labels: tuple[str, ...] = Field(max_length=14)
    execution_plan: tuple[str, ...] = Field(max_length=8)
    dry_run: bool
