from typing import Optional

from pydantic import BaseModel


class DiscordChannel(BaseModel):
    id: str
    name: str
    type: int
    position: int = 0
    parent_id: Optional[str] = None


class DiscordRole(BaseModel):
    id: str
    name: str
    color: int = 0
    position: int = 0
    permissions: int = 0
    managed: bool = False
    mentionable: bool = False


class DiscordMember(BaseModel):
    id: str
    username: str
    display_name: str
    avatar: Optional[str] = None
