export type Theme = "dark" | "light";
export type ActivityUserType = "standard" | "streamer" | "developer" | "admin";
export type AccessLevel = "ordinary" | "creator" | "developer" | "moderator" | "administrator";
export type PermissionLevel = "disabled" | "view" | "edit" | "publish" | "manage";

export type ModuleKey =
  | "dashboard"
  | "access"
  | "welcome"
  | "role-panels"
  | "creator-alerts"
  | "dev-blog"
  | "ai-moderator"
  | "logs"
  | "server-stats"
  | "voice-rooms"
  | "bot-settings"
  | "integrations"
  | "health";

export type ActivityUser = {
  id: string;
  username: string;
  discriminator?: string | null;
  global_name?: string | null;
  avatar?: string | null;
};

export type ActivityAccess = {
  is_admin: boolean;
  is_streamer: boolean;
  is_developer: boolean;
};

export type ActivitySession = {
  user: ActivityUser;
  guild_id: string;
  user_type: ActivityUserType;
  access: ActivityAccess;
  is_admin: boolean;
};

export type PanelSession = ActivitySession & {
  access_level: AccessLevel;
  permissions: Record<ModuleKey, PermissionLevel>;
  available_modules: ModuleKey[];
};

export type WelcomeConfig = {
  guild_id: number;
  title: string;
  description: string;
  thumbnail_url: string | null;
  footer_text: string | null;
  footer_icon_url: string | null;
  color: number;
  is_enabled: boolean;
  rules_channel_id: number | null;
  roles_channel_id: number | null;
};

export type PanelModule = {
  key: ModuleKey;
  title: string;
  eyebrow: string;
  description: string;
  status: "online" | "configured" | "draft" | "attention" | "locked";
  permission: PermissionLevel;
};

export type DashboardMetric = {
  label: string;
  value: string;
  delta: string;
  tone: "neutral" | "success" | "warning" | "danger";
};

export type TimelineEvent = {
  id: string;
  title: string;
  detail: string;
  time: string;
  tone: "neutral" | "success" | "warning" | "danger";
};

export type HealthSignal = {
  name: string;
  value: string;
  status: "operational" | "degraded" | "offline";
  latency_ms?: number | null;
};

export type ActivityHealth = {
  guild_id: string;
  signals: HealthSignal[];
  bot_latency_ms: number | null;
};

export type AccessMatrixRow = {
  role: AccessLevel;
  permissions: Record<ModuleKey, PermissionLevel>;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  scope: string;
};
