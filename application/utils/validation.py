import re


REASON_SAFE_PATTERN = re.compile(
    r"^["
    r"\w"
    r"\s"
    r"\u0400-\u04FF"
    r"\u0500-\u052F"
    r"\u2DE0-\u2DFF"
    r"\uA640-\uA69F"
    r"\u0370-\u03FF"
    r"，。！？；：""''【】《》（）"
    r",.!?;:\-\–\—"
    r"\(\)\[\]\{\}"
    r"@\#\$\%\^\&\*\+\=\|\<\>"
    r"~`"
    r"]+$",
    re.UNICODE,
)


def validate_reason(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("Reason must not be empty")
    if not REASON_SAFE_PATTERN.match(value):
        raise ValueError(
            "Reason contains disallowed characters. "
            "Only letters, numbers, spaces, and basic punctuation are allowed."
        )
    lowered = value.lower()
    if "http://" in lowered or "https://" in lowered or "discord.gg/" in lowered:
        raise ValueError("Links are not allowed in reason")
    if "`" in value or "||" in value:
        raise ValueError("Markdown injection is not allowed in reason")
    if len(value) > 500:
        raise ValueError("Reason must not exceed 500 characters")
    return value.strip()


def validate_duration_seconds(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    if value <= 0:
        raise ValueError("Duration must be greater than 0 seconds")
    return value


def validate_user_id(value: int) -> int:
    if value <= 0:
        raise ValueError("Invalid Discord user ID")
    return value
