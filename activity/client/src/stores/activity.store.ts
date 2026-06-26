import { defineStore } from "pinia";
import { DiscordSDK } from "@discord/embedded-app-sdk";
import type { CommandResponse } from "@discord/embedded-app-sdk";
import {
  exchangeDiscordCode,
  createDevBlogPost,
  deleteVoiceRoom,
  getActivityHealth,
  getActivityRoles,
  getActivitySession,
  getBotSettings,
  getChannelPurposes,
  getCreatorAlertSources,
  getDevBlogPosts,
  getDiscordChannels,
  getDiscordRoles,
  getIntegrations,
  getLogs,
  getServerStats,
  getVoiceRooms,
  getWelcomeConfig,
  previewCreatorAlert,
  resetWelcomeConfig,
  saveActivityRole,
  saveChannelPurpose,
  saveCreatorAlertSource,
  saveWelcomeConfig,
  searchUserStats,
  updateVoiceRoom,
} from "../api/activity.api";
import {
  administratorPermissions,
  healthSignals as mockHealthSignals,
  mockSession,
  mockWelcome,
} from "./mock-data";
import type {
  ActivityHealth,
  ActivitySession,
  ActivityRolePurpose,
  AccessLevel,
  ChannelPurpose,
  CreatorAlertSource,
  DevBlogDraft,
  DiscordChannel,
  DiscordRole,
  HealthSignal,
  LogsPayload,
  ModuleKey,
  PanelSession,
  PermissionLevel,
  ServerStatsPayload,
  Theme,
  WelcomeConfig,
  VoiceRoom,
} from "../types/activity.types";

type Auth = CommandResponse<"authenticate">;

type State = {
  booted: boolean;
  loading: boolean;
  error: string | null;
  mode: "local" | "discord";
  theme: Theme;
  token: string | null;
  session: PanelSession | null;
  welcome: WelcomeConfig;
  healthSignals: HealthSignal[];
  botLatencyMs: number | null;
  healthLoading: boolean;
  healthError: string | null;
  lastHealthRefresh: number;
  moduleLoading: boolean;
  moduleError: string | null;
  textChannels: DiscordChannel[];
  voiceChannels: DiscordChannel[];
  roles: DiscordRole[];
  channelPurposes: Partial<Record<ChannelPurpose, number>>;
  activityRoles: Partial<Record<ActivityRolePurpose, number>>;
  devBlogPosts: Array<Record<string, unknown>>;
  creatorSources: CreatorAlertSource[];
  creatorPreview: Record<string, unknown> | null;
  voiceRooms: VoiceRoom[];
  serverStats: ServerStatsPayload | null;
  userStatsResults: Array<Record<string, unknown>>;
  logs: LogsPayload | null;
  botSettings: Record<string, unknown> | null;
  integrations: Record<string, unknown> | null;
  discordSdk: DiscordSDK | null;
  auth: Auth | null;
};

export const useActivityStore = defineStore("activity", {
  state: (): State => ({
    booted: false,
    loading: false,
    error: null,
    mode: "local",
    theme: "dark",
    token: null,
    session: null,
    welcome: mockWelcome,
    healthSignals: mockHealthSignals,
    botLatencyMs: 42,
    healthLoading: false,
    healthError: null,
    lastHealthRefresh: 0,
    moduleLoading: false,
    moduleError: null,
    textChannels: [],
    voiceChannels: [],
    roles: [],
    channelPurposes: {},
    activityRoles: {},
    devBlogPosts: [],
    creatorSources: [],
    creatorPreview: null,
    voiceRooms: [],
    serverStats: null,
    userStatsResults: [],
    logs: null,
    botSettings: null,
    integrations: null,
    discordSdk: null,
    auth: null,
  }),

  getters: {
    isAdmin: (state) => state.session?.access_level === "administrator",
    displayName: (state) =>
      state.session?.user.global_name || state.session?.user.username || "Omni user",
    availableModules: (state) => state.session?.available_modules ?? [],
  },

  actions: {
    async boot() {
      if (this.booted || this.loading) return;

      this.loading = true;
      this.error = null;

      try {
        if (!isDiscordActivityLaunch()) {
          this.useLocalPreview();
          return;
        }

        await this.bootDiscordActivity();
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error);
        if (!this.session) {
          this.useLocalPreview();
        }
      } finally {
        this.loading = false;
        this.booted = true;
      }
    },

    useLocalPreview() {
      this.mode = "local";
      this.token = null;
      this.auth = null;
      this.discordSdk = null;
      this.session = mockSession;
      this.welcome = mockWelcome;
      this.healthSignals = mockHealthSignals;
      this.botLatencyMs = 42;
      this.healthError = null;
      this.textChannels = [
        { id: "1515345327903867114", name: "welcome", type: 0, position: 1 },
        { id: "1515345327903867115", name: "dev-blog", type: 0, position: 2 },
        { id: "1515345327903867116", name: "stream-alerts", type: 0, position: 3 },
      ];
      this.voiceChannels = [{ id: "1516082233121702031", name: "Create room", type: 2, position: 1 }];
      this.roles = [
        { id: "1", name: "Admin", color: 0x5865f2, position: 10, managed: false, mentionable: true },
        { id: "2", name: "Streamer", color: 0x8b5cf6, position: 9, managed: false, mentionable: true },
        { id: "3", name: "Developer", color: 0x22c55e, position: 8, managed: false, mentionable: true },
      ];
      this.channelPurposes = { welcome: 1515345327903867114, dev_blog: 1515345327903867115, stream_announce: 1515345327903867116 };
      this.activityRoles = { activity_admin: 1, activity_streamer: 2, activity_developer: 3 };
    },

    async bootDiscordActivity() {
      const clientId = import.meta.env.VITE_DISCORD_CLIENT_ID;
      if (!clientId) {
        throw new Error("VITE_DISCORD_CLIENT_ID is required for Discord Activity launch.");
      }

      this.mode = "discord";
      const discordSdk = new DiscordSDK(clientId);
      this.discordSdk = discordSdk;
      await discordSdk.ready();

      const { code } = await discordSdk.commands.authorize({
        client_id: clientId,
        response_type: "code",
        state: "",
        prompt: "none",
        scope: ["identify", "guilds", "applications.commands"],
      });

      const token = await exchangeDiscordCode(code);
      this.token = token.access_token;
      this.auth = await discordSdk.commands.authenticate({
        access_token: token.access_token,
      });

      if (!this.auth) {
        throw new Error("Discord authentication failed.");
      }

      if (!discordSdk.guildId) {
        this.session = {
          ...mockSession,
          user: this.auth.user,
          guild_id: "0",
          access_level: "ordinary",
          available_modules: [],
          permissions: emptyPermissions(),
          is_admin: false,
        };
        return;
      }

      const activitySession = await getActivitySession(discordSdk.guildId, token.access_token);
      this.session = toPanelSession(activitySession);

      if (this.session.is_admin) {
        this.welcome = await getWelcomeConfig(discordSdk.guildId, token.access_token);
      }

      await this.loadReferenceData();
      await this.refreshHealth(true);
    },

    toggleTheme() {
      this.theme = this.theme === "dark" ? "light" : "dark";
    },

    can(module: ModuleKey, level: PermissionLevel = "view") {
      const permission = this.session?.permissions[module] ?? "disabled";
      return permissionRank(permission) >= permissionRank(level);
    },

    async saveWelcome(next: WelcomeConfig) {
      if (!this.token || this.mode === "local") {
        this.welcome = next;
        return;
      }

      this.welcome = await saveWelcomeConfig(next, this.token);
    },

    async resetWelcome() {
      if (!this.session) return;

      if (!this.token || this.mode === "local") {
        this.welcome = { ...mockWelcome, guild_id: Number(this.session.guild_id) || mockWelcome.guild_id };
        return;
      }

      this.welcome = await resetWelcomeConfig(this.session.guild_id, this.token);
    },

    async refreshHealth(force = false) {
      if (!this.session || !this.can("health")) return;

      const now = Date.now();
      if (!force && now - this.lastHealthRefresh < 10_000) {
        return;
      }

      if (!this.token || this.mode === "local") {
        this.lastHealthRefresh = now;
        this.healthSignals = mockHealthSignals;
        this.botLatencyMs = 42;
        return;
      }

      this.healthLoading = true;
      this.healthError = null;

      try {
        const health = await getActivityHealth(this.session.guild_id, this.token);
        this.applyHealth(health);
        this.lastHealthRefresh = Date.now();
      } catch (error) {
        this.healthError = error instanceof Error ? error.message : String(error);
      } finally {
        this.healthLoading = false;
      }
    },

    applyHealth(health: ActivityHealth) {
      this.healthSignals = health.signals;
      this.botLatencyMs = health.bot_latency_ms;
    },

    async loadReferenceData() {
      if (!this.session || !this.token || this.mode === "local") return;
      const guildId = this.session.guild_id;
      const [textChannels, voiceChannels, channelPurposes] = await Promise.all([
        getDiscordChannels(guildId, this.token, "text"),
        getDiscordChannels(guildId, this.token, "voice"),
        getChannelPurposes(guildId, this.token),
      ]);
      this.textChannels = textChannels;
      this.voiceChannels = voiceChannels;
      this.channelPurposes = channelPurposes;

      if (this.isAdmin) {
        const [roles, activityRoles] = await Promise.all([
          getDiscordRoles(guildId, this.token),
          getActivityRoles(guildId, this.token),
        ]);
        this.roles = roles;
        this.activityRoles = activityRoles;
      }
    },

    async loadModuleData(module: ModuleKey) {
      if (!this.session || !this.can(module)) return;
      if (!this.token || this.mode === "local") return;

      this.moduleLoading = true;
      this.moduleError = null;
      try {
        const guildId = this.session.guild_id;
        if (module === "dashboard") {
          await Promise.all([
            this.refreshHealth(true),
            getLogs(guildId, this.token).then((logs) => {
              this.logs = logs;
            }),
            getServerStats(guildId, this.token).then((stats) => {
              this.serverStats = stats;
            }),
          ]);
        } else if (module === "access") {
          await this.loadReferenceData();
        } else if (module === "dev-blog") {
          this.devBlogPosts = await getDevBlogPosts(guildId, this.token);
        } else if (module === "creator-alerts") {
          this.creatorSources = await getCreatorAlertSources(guildId, this.token);
        } else if (module === "voice-rooms") {
          this.voiceRooms = await getVoiceRooms(guildId, this.token);
        } else if (module === "server-stats") {
          this.serverStats = await getServerStats(guildId, this.token);
        } else if (module === "logs") {
          this.logs = await getLogs(guildId, this.token);
        } else if (module === "bot-settings") {
          this.botSettings = await getBotSettings(guildId, this.token);
        } else if (module === "integrations") {
          this.integrations = await getIntegrations(guildId, this.token);
        } else if (module === "health") {
          await this.refreshHealth(true);
        }
      } catch (error) {
        this.moduleError = error instanceof Error ? error.message : String(error);
      } finally {
        this.moduleLoading = false;
      }
    },

    async saveActivityRolePurpose(purpose: ActivityRolePurpose, roleId: string) {
      if (!this.session || !this.token || this.mode === "local") {
        this.activityRoles[purpose] = Number(roleId);
        return;
      }
      this.activityRoles = await saveActivityRole(this.session.guild_id, this.token, purpose, roleId);
    },

    async saveChannelPurposeValue(purpose: ChannelPurpose, channelId: string) {
      if (!this.session || !this.token || this.mode === "local") {
        this.channelPurposes[purpose] = Number(channelId);
        return;
      }
      this.channelPurposes = await saveChannelPurpose(this.session.guild_id, this.token, purpose, channelId);
    },

    async createDevBlog(draft: Omit<DevBlogDraft, "guild_id">) {
      if (!this.session || !this.token) return;
      await createDevBlogPost({ guild_id: Number(this.session.guild_id), ...draft }, this.token);
      await this.loadModuleData("dev-blog");
    },

    async saveCreatorSource(source: Omit<CreatorAlertSource, "guild_id">) {
      if (!this.session || !this.token) return;
      await saveCreatorAlertSource({ guild_id: Number(this.session.guild_id), ...source }, this.token);
      await this.loadModuleData("creator-alerts");
    },

    async previewCreatorSource(source: Omit<CreatorAlertSource, "guild_id">) {
      if (!this.session || !this.token) return;
      this.creatorPreview = await previewCreatorAlert({ guild_id: Number(this.session.guild_id), ...source }, this.token);
    },

    async updateVoice(channelId: number, payload: Record<string, unknown>) {
      if (!this.session || !this.token) return;
      await updateVoiceRoom(this.session.guild_id, this.token, channelId, payload);
      await this.loadModuleData("voice-rooms");
    },

    async deleteVoice(channelId: number) {
      if (!this.session || !this.token) return;
      await deleteVoiceRoom(this.session.guild_id, this.token, channelId);
      await this.loadModuleData("voice-rooms");
    },

    async searchStatsUsers(query: string) {
      if (!this.session || !this.token || !query.trim()) {
        this.userStatsResults = [];
        return;
      }
      this.userStatsResults = await searchUserStats(this.session.guild_id, this.token, query.trim());
    },

    async loadLogs(source = "all", eventType = "", query = "") {
      if (!this.session || !this.token || this.mode === "local") return;
      this.logs = await getLogs(this.session.guild_id, this.token, source, eventType, query);
    },
  },
});

function isDiscordActivityLaunch() {
  const params = new URLSearchParams(window.location.search);
  return params.has("frame_id") || params.has("instance_id");
}

function toPanelSession(session: ActivitySession): PanelSession {
  const accessLevel = resolveAccessLevel(session);
  const permissions = resolvePermissions(accessLevel);

  return {
    ...session,
    access_level: accessLevel,
    permissions,
    available_modules: Object.entries(permissions)
      .filter(([, permission]) => permission !== "disabled")
      .map(([module]) => module as ModuleKey),
  };
}

function resolveAccessLevel(session: ActivitySession): AccessLevel {
  if (session.is_admin) return "administrator";
  if (session.access.is_developer) return "developer";
  if (session.access.is_streamer) return "creator";
  return "ordinary";
}

function resolvePermissions(level: AccessLevel): Record<ModuleKey, PermissionLevel> {
  if (level === "administrator") return administratorPermissions;

  const permissions = emptyPermissions();
  permissions.dashboard = "view";
  permissions.health = "view";

  if (level === "developer") {
    permissions["dev-blog"] = "publish";
  }

  if (level === "creator") {
    permissions["creator-alerts"] = "edit";
  }

  if (level === "moderator") {
    permissions["ai-moderator"] = "view";
    permissions.logs = "view";
  }

  return permissions;
}

function emptyPermissions(): Record<ModuleKey, PermissionLevel> {
  return {
    dashboard: "disabled",
    access: "disabled",
    welcome: "disabled",
    "role-panels": "disabled",
    "creator-alerts": "disabled",
    "dev-blog": "disabled",
    "ai-moderator": "disabled",
    logs: "disabled",
    "server-stats": "disabled",
    "voice-rooms": "disabled",
    "bot-settings": "disabled",
    integrations: "disabled",
    health: "disabled",
  };
}

function permissionRank(permission: PermissionLevel) {
  return {
    disabled: 0,
    view: 1,
    edit: 2,
    publish: 3,
    manage: 4,
  }[permission];
}
