from enum import StrEnum


class AiModerationAction(StrEnum):
    IGNORE = "IGNORE"
    LOG = "LOG"
    REVIEW = "REVIEW"
    WARN = "WARN"
    DELETE = "DELETE"
    DELETE_WARN = "DELETE_WARN"
    TIMEOUT = "TIMEOUT"
    KICK = "KICK"
    BAN = "BAN"
