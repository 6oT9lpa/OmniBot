import type {
  AccessLevel,
  AccessMatrixRow,
  DashboardMetric,
  HealthSignal,
  ModuleKey,
  PanelModule,
  PanelSession,
  PermissionLevel,
  TimelineEvent,
  WelcomeConfig,
} from "../types/activity.types";

export const moduleOrder: ModuleKey[] = [
  "dashboard",
  "access",
  "welcome",
  "role-panels",
  "creator-alerts",
  "dev-blog",
  "ai-moderator",
  "logs",
  "server-stats",
  "voice-rooms",
  "bot-settings",
  "integrations",
  "health",
];

export const defaultVisibleModules: ModuleKey[] = [
  "dashboard",
  "integrations",
  "health",
  "server-stats",
  "voice-rooms",
];

export const accessConfigurableModules: ModuleKey[] = [
  "welcome",
  "role-panels",
  "creator-alerts",
  "dev-blog",
  "ai-moderator",
  "logs",
  "bot-settings",
];

export const moduleLabels: Record<ModuleKey, string> = {
  dashboard: "Dashboard",
  access: "Access Roles",
  welcome: "Welcome Alerts",
  "role-panels": "Role Panels",
  "creator-alerts": "Creator Alerts",
  "dev-blog": "Dev Blog",
  "ai-moderator": "AI Metrics",
  logs: "Logs",
  "server-stats": "Server Stats",
  "voice-rooms": "Voice Rooms",
  "bot-settings": "Bot Settings",
  integrations: "Integrations",
  health: "Health Status",
};

export const moduleDescriptions: Record<ModuleKey, string> = {
  dashboard: "Live overview of modules, activity and configuration health.",
  access: "Map Activity roles to tab permissions.",
  welcome: "Design welcome messages with variables, preview and publishing checks.",
  "role-panels": "Build role menus with buttons, select menus and validation states.",
  "creator-alerts": "Manage Twitch, YouTube and future creator source notifications.",
  "dev-blog": "Compose developer updates with embeds, links, images and CTA buttons.",
  "ai-moderator": "Analytics-first AI moderation signals without direct punishment actions.",
  logs: "Filter server events, member events, punishments and AI flags.",
  "server-stats": "Track members, messages, voice activity and leaderboards.",
  "voice-rooms": "Configure dynamic voice triggers, room naming and cleanup rules.",
  "bot-settings": "Control defaults, module toggles, language and embed styling.",
  integrations: "Monitor Discord, creator platforms, database and Ollama status.",
  health: "Operational heartbeat for bot, API, database and background workers.",
};

export const administratorPermissions = moduleOrder.reduce(
  (permissions, key) => ({ ...permissions, [key]: "manage" as PermissionLevel }),
  {} as Record<ModuleKey, PermissionLevel>,
);

export const mockSession: PanelSession = {
  user: {
    id: "local-preview",
    username: "local-admin",
    global_name: "Local Administrator",
  },
  guild_id: "1517163246862471249",
  user_type: "admin",
  access: {
    is_admin: true,
    is_streamer: true,
    is_developer: true,
  },
  access_level: "administrator",
  activity_roles: ["Administrator"],
  permissions: administratorPermissions,
  available_modules: moduleOrder,
  is_admin: true,
};

export const mockWelcome: WelcomeConfig = {
  guild_id: 1517163246862471249,
  title: "Welcome to Omni",
  description:
    "Hello {user}. You joined {server}, a community powered by automation, creator tools and clean Discord workflows.",
  thumbnail_url: null,
  footer_text: "OmniBot Activity",
  footer_icon_url: null,
  color: 0x5865f2,
  is_enabled: true,
  rules_channel_id: null,
  roles_channel_id: null,
};

export const dashboardMetrics: DashboardMetric[] = [
  { label: "Modules ready", value: "8/13", delta: "+3 planned", tone: "success" },
  { label: "AI checks today", value: "12.8k", delta: "2.1% flagged", tone: "neutral" },
  { label: "Creator sources", value: "14", delta: "3 waiting auth", tone: "warning" },
  { label: "Bot latency", value: "42 ms", delta: "stable", tone: "success" },
];

export const timelineEvents: TimelineEvent[] = [
  {
    id: "1",
    title: "Welcome module edited",
    detail: "Administrator updated the server entry message and preview variables.",
    time: "2 min ago",
    tone: "success",
  },
  {
    id: "2",
    title: "Creator alert source pending",
    detail: "A YouTube channel is waiting for ownership verification.",
    time: "19 min ago",
    tone: "warning",
  },
  {
    id: "3",
    title: "AI moderation scan complete",
    detail: "12,842 messages checked with no high-risk trend detected.",
    time: "1 hour ago",
    tone: "neutral",
  },
];

export const healthSignals: HealthSignal[] = [
  { name: "Discord Gateway", value: "Online", status: "operational" },
  { name: "Activity API", value: "Serving", status: "operational" },
  { name: "SQLite", value: "Connected", status: "operational" },
  { name: "Ollama", value: "Not linked", status: "degraded" },
  { name: "Stream Checker", value: "Mock mode", status: "degraded" },
];

export function buildModules(session: PanelSession): PanelModule[] {
  const roleLabel = session.activity_roles[0] || session.access_level;
  return moduleOrder.map((key) => {
    const permission = session.permissions[key] ?? "disabled";
    return {
      key,
      title: moduleLabels[key],
      eyebrow: permission === "disabled" ? "Locked" : roleLabel,
      description: moduleDescriptions[key],
      permission,
      status: permission === "disabled" ? "locked" : key === "health" ? "online" : key === "dev-blog" ? "draft" : "configured",
    };
  });
}

export const accessMatrix: AccessMatrixRow[] = [
  row("ordinary", defaultVisibleModules, "view"),
  row("creator", [...defaultVisibleModules, "creator-alerts"], "edit"),
  row("developer", [...defaultVisibleModules, "dev-blog"], "publish"),
  row("moderator", [...defaultVisibleModules, "ai-moderator", "logs"], "view"),
  row("administrator", moduleOrder, "manage"),
];

function row(role: AccessLevel, keys: ModuleKey[], level: PermissionLevel): AccessMatrixRow {
  const permissions = moduleOrder.reduce(
    (acc, key) => ({ ...acc, [key]: keys.includes(key) ? level : "disabled" }),
    {} as Record<ModuleKey, PermissionLevel>,
  );

  return { role, permissions };
}
