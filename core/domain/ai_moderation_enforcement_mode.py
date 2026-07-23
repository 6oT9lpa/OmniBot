from enum import StrEnum


class AiModerationEnforcementMode(StrEnum):
    SHADOW = "SHADOW"
    LIMITED = "LIMITED"
    ELEVATED = "ELEVATED"
