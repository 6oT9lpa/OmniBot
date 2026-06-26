import { defineStore } from "pinia";
import { DiscordSDK } from "@discord/embedded-app-sdk";
import type { CommandResponse } from "@discord/embedded-app-sdk";
import {
  exchangeDiscordCode,
  getActivityHealth,
  getActivitySession,
  getWelcomeConfig,
  resetWelcomeConfig,
  saveWelcomeConfig,
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
  AccessLevel,
  HealthSignal,
  ModuleKey,
  PanelSession,
  PermissionLevel,
  Theme,
  WelcomeConfig,
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
