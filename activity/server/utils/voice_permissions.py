from typing import Any


CONNECT_BIT = 0x00100000
VIEW_CHANNEL_BIT = 0x00000400


def build_voice_lock_overwrites(channel: dict[str, Any], guild_id: int, locked: bool) -> list[dict[str, Any]]:
    overwrites = list(channel.get("permission_overwrites", []))
    everyone_id = str(guild_id)
    matched = False

    for overwrite in overwrites:
        if overwrite.get("id") == everyone_id and overwrite.get("type") == 0:
            allow = int(overwrite.get("allow", "0"))
            deny = int(overwrite.get("deny", "0"))
            if locked:
                deny |= CONNECT_BIT
                allow &= ~CONNECT_BIT
            else:
                allow |= CONNECT_BIT
                deny &= ~CONNECT_BIT
            overwrite["allow"] = str(allow)
            overwrite["deny"] = str(deny)
            matched = True
            break

    if not matched:
        overwrites.append(
            {
                "id": everyone_id,
                "type": 0,
                "allow": "0" if locked else str(CONNECT_BIT),
                "deny": str(CONNECT_BIT) if locked else "0",
            }
        )

    return overwrites


def build_member_connect_overwrites(
    channel: dict[str, Any],
    user_id: int,
    *,
    allowed: bool,
) -> list[dict[str, Any]]:
    # Reuse Discord overwrite bits for invite and ban actions from the Activity panel.
    overwrites = list(channel.get("permission_overwrites", []))
    member_id = str(user_id)
    matched = False

    for overwrite in overwrites:
        if overwrite.get("id") == member_id and overwrite.get("type") == 1:
            allow = int(overwrite.get("allow", "0"))
            deny = int(overwrite.get("deny", "0"))
            if allowed:
                allow |= CONNECT_BIT | VIEW_CHANNEL_BIT
                deny &= ~CONNECT_BIT
            else:
                deny |= CONNECT_BIT
                allow &= ~CONNECT_BIT
            overwrite["allow"] = str(allow)
            overwrite["deny"] = str(deny)
            matched = True
            break

    if not matched:
        overwrites.append(
            {
                "id": member_id,
                "type": 1,
                "allow": str(CONNECT_BIT | VIEW_CHANNEL_BIT) if allowed else "0",
                "deny": "0" if allowed else str(CONNECT_BIT),
            }
        )

    return overwrites
