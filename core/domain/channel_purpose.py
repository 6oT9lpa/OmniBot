from enum import Enum


class ChannelPurpose(str, Enum):
    WELCOME = "welcome"
    MEMBER_LOG = "member_log"
    MOD_LOG = "mod_log"
    MESSAGE_LOG = "message_log"
    VOICE_LOG = "voice_log"
    STREAM_ANNOUNCE = "stream_announce"
    DEV_BLOG = "dev_blog"
    ADMIN_LOG = "admin_log"