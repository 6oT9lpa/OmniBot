from enum import Enum


class ChannelPurpose(str, Enum):
    WELCOME = "welcome"
    MEMBER_LOG = "member_log"
    MOD_LOG = "mod_log"
    MESSAGE_LOG = "message_log"
    CHANNEL_LOG = "channel_log" 
    STREAM_ANNOUNCE = "stream_announce"
    DEV_BLOG = "dev_blog"
    AI_MODERATION_LOG = "ai_moderation_log"
