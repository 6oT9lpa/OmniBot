from typing import Optional

from infrastructure.config import get_config, BotConfig
from infrastructure.database.connection import DatabaseManager
from infrastructure.database import DatabaseManager
from infrastructure.database import (
    RoleRepository,
    WelcomeConfigRepository,
    ChannelConfigRepository,
    RolePanelMessageRepository,
    RolePanelButtonRepository,
    MessageLogRepository,
    GuildEventLogRepository,
    PunishmentRepository,
    StatsRepository,
    VoiceRepository,
    ServerRolePurposeRepository
)
from application.services import (
    RoleService,
    WelcomeService,
    ChannelService,
    AuditLogService,
    LoggingService,
    ModerationHistoryService,
    ModeratorService,
    VoiceService,
    StatsService,
    ServerRolePurposeService
)
from infrastructure.logging import get_logger
from di.modules import MemberEventsModule, LoggingModule, ModerationModule

logger = get_logger(__name__)


class Container:
    def __init__(self):
        self.config: BotConfig = get_config()
        
        self._database: Optional[DatabaseManager] = None
        self._role_repo: Optional[RoleRepository] = None
        self._role_service: Optional[RoleService] = None
        self._stats_service: Optional[StatsService] = None
        self._stats_repo: Optional[StatsRepository] = None
        self._voice_service: Optional[VoiceService] = None
        self._voice_repo: Optional[VoiceRepository] = None
        self._server_role_purpose_repo: Optional[ServerRolePurposeRepository] = None
        self._panel_message_repo: Optional[RolePanelMessageRepository] = None
        self._panel_button_repo: Optional[RolePanelButtonRepository] = None
        self._channel_config_repo: Optional[ChannelConfigRepository] = None
        self._channel_service: Optional[ChannelService] = None
        self._welcome_config_repo: Optional[WelcomeConfigRepository] = None
        self._welcome_service: Optional[WelcomeService] = None
        self._message_log_repo: Optional[MessageLogRepository] = None
        self._guild_event_log_repo: Optional[GuildEventLogRepository] = None
        self._punishment_repo: Optional[PunishmentRepository] = None
        self._audit_log_service: Optional[AuditLogService] = None
        self._logging_service: Optional[LoggingService] = None
        self._moderation_history_service: Optional[ModerationHistoryService] = None
        self._moderator_service: Optional[ModeratorService] = None
        self._server_role_purpose_service: Optional[ServerRolePurposeService] = None
        self._member_events_module: Optional[MemberEventsModule] = None
        self._logging_module: Optional[LoggingModule] = None
        self._moderation_module: Optional[ModerationModule] = None

        logger.info("DI Container initialized")

    async def get_database(self) -> DatabaseManager:
        if not self._database:
            self._database = DatabaseManager(self.config.database_url)
            await self._database.connect()
            await self._database.initialize()
        return self._database
    
    #=============== Repository =====================
    async def get_role_repository(self) -> RoleRepository:
        if not self._role_repo:
            db = await self.get_database()
            self._role_repo = RoleRepository(db, default_guild_id=self.config.discord_guild_id)
        return self._role_repo
    
    async def get_panel_message_repository(self) -> RolePanelMessageRepository:
        if not self._panel_message_repo:
            db = await self.get_database()
            self._panel_message_repo = RolePanelMessageRepository(db)
        return self._panel_message_repo
    
    async def get_panel_button_repository(self) -> RolePanelButtonRepository:
        if not self._panel_button_repo:
            db = await self.get_database()
            self._panel_button_repo = RolePanelButtonRepository(db)
        return self._panel_button_repo
    
    async def get_channel_config_repository(self) -> ChannelConfigRepository:
        if not self._channel_config_repo:
            db = await self.get_database()
            self._channel_config_repo = ChannelConfigRepository(db)
        return self._channel_config_repo
    
    async def get_welcome_config_repository(self) -> WelcomeConfigRepository:
        if not self._welcome_config_repo:
            db = await self.get_database()
            self._welcome_config_repo = WelcomeConfigRepository(db)
        return self._welcome_config_repo

    async def get_message_log_repository(self) -> MessageLogRepository:
        if not self._message_log_repo:
            db = await self.get_database()
            self._message_log_repo = MessageLogRepository(db)
        return self._message_log_repo

    async def get_guild_event_log_repository(self) -> GuildEventLogRepository:
        if not self._guild_event_log_repo:
            db = await self.get_database()
            self._guild_event_log_repo = GuildEventLogRepository(db)
        return self._guild_event_log_repo

    async def get_punishment_repository(self) -> PunishmentRepository:
        if not self._punishment_repo:
            db = await self.get_database()
            self._punishment_repo = PunishmentRepository(db)
        return self._punishment_repo
    
    async def get_stats_repository(self) -> StatsRepository:
        if not self._stats_repo:
            db = await self.get_database()
            self._stats_repo = StatsRepository(db)
        return self._stats_repo
    
    async def get_voice_repository(self) -> VoiceRepository:
        if not self._voice_repo:
            db = await self.get_database()
            self._voice_repo = VoiceRepository(db)
        return self._voice_repo

    async def get_server_role_purpose_repository(self) -> ServerRolePurposeRepository:
        if not self._server_role_purpose_repo:
            db = await self.get_database()
            self._server_role_purpose_repo = ServerRolePurposeRepository(db)
        return self._server_role_purpose_repo

    #=============== Service =====================

    async def get_stats_service(self) -> StatsService:
        if not self._stats_service:
            repo = await self.get_stats_repository()
            self._stats_service = StatsService(repo)
        return self._stats_service
    
    async def get_voice_service(self) -> VoiceService:
        if not self._voice_service:
            repo = await self.get_voice_repository()
            logging_service = await self.get_logging_service()
            self._voice_service = VoiceService(repo, logging_service)
        return self._voice_service

    async def get_server_role_purpose_service(self) -> ServerRolePurposeService:
        if not self._server_role_purpose_service:
            repo = await self.get_server_role_purpose_repository()
            self._server_role_purpose_service = ServerRolePurposeService(repo)
            logger.info("ServerRolePurposeService created")
        return self._server_role_purpose_service

    async def get_role_service(self) -> RoleService:
        if not self._role_service:
            repo = await self.get_role_repository()
            self._role_service = RoleService(repo, self.config)
            
            panel_message_repo = await self.get_panel_message_repository()
            panel_button_repo = await self.get_panel_button_repository()
            self._role_service.set_panel_repositories(panel_message_repo, panel_button_repo)
            
            logger.info("RoleService created with panel repositories")
            
        return self._role_service

    async def get_welcome_service(self) -> WelcomeService:
        if not self._welcome_service:
            repo = await self.get_welcome_config_repository()
            self._welcome_service = WelcomeService(repo)
            logger.info("WelcomeService created")
        return self._welcome_service
    
    async def get_channel_service(self) -> ChannelService:
        if not self._channel_service:
            repo = await self.get_channel_config_repository()
            self._channel_service = ChannelService(repo)
            logger.info("ChannelService created")
        return self._channel_service

    async def get_audit_log_service(self) -> AuditLogService:
        if not self._audit_log_service:
            channel_service = await self.get_channel_service()
            self._audit_log_service = AuditLogService(self.config, channel_service)
            logger.info("AuditLogService created")
        return self._audit_log_service

    async def get_logging_service(self) -> LoggingService:
        if not self._logging_service:
            message_repo = await self.get_message_log_repository()
            guild_event_repo = await self.get_guild_event_log_repository()
            audit_log_service = await self.get_audit_log_service()
            self._logging_service = LoggingService(
                message_repo,
                guild_event_repo,
                audit_log_service,
                self.config,
            )
            logger.info("LoggingService created")
        return self._logging_service

    async def get_moderation_history_service(self) -> ModerationHistoryService:
        if not self._moderation_history_service:
            punishment_repo = await self.get_punishment_repository()
            self._moderation_history_service = ModerationHistoryService(punishment_repo)
            logger.info("ModerationHistoryService created")
        return self._moderation_history_service

    async def get_moderator_service(self) -> ModeratorService:
        if not self._moderator_service:
            punishment_repo = await self.get_punishment_repository()
            logging_service = await self.get_logging_service()
            history_service = await self.get_moderation_history_service()
            self._moderator_service = ModeratorService(
                punishment_repo,
                logging_service,
                history_service,
            )
            logger.info("ModeratorService created")
        return self._moderator_service
    
    def get_member_events_module(self) -> MemberEventsModule:
        if not self._member_events_module:
            self._member_events_module = MemberEventsModule(self)
        return self._member_events_module

    def get_logging_module(self) -> LoggingModule:
        if not self._logging_module:
            self._logging_module = LoggingModule(self)
        return self._logging_module

    def get_moderation_module(self) -> ModerationModule:
        if not self._moderation_module:
            self._moderation_module = ModerationModule(self)
        return self._moderation_module
    
    async def shutdown(self):
        if self._database:
            await self._database.close()
        
        if self._member_events_module:
            await self._member_events_module.shutdown()
        if self._logging_module:
            await self._logging_module.shutdown()
        if self._moderation_module:
            await self._moderation_module.shutdown()
        
        logger.info("Container shutdown complete")
