import { apiRequest } from "./client";
import type {
  ActivityHealth,
  ActivityRolePurpose,
  ActivitySession,
  ChannelPurpose,
  CreatorAlertSource,
  DevBlogDraft,
  DiscordChannel,
  DiscordMember,
  DiscordRole,
  LogsPayload,
  ServerStatsPayload,
  TokenResponse,
  VoiceRoom,
  WelcomeConfig,
} from "../types/activity.types";

export function exchangeDiscordCode(code: string) {
  return apiRequest<TokenResponse>("/api/auth/token", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export function getActivitySession(guildId: string, token: string) {
  return apiRequest<ActivitySession>(`/api/activity/session?guild_id=${guildId}`, {}, token);
}

export function getActivityHealth(guildId: string, token: string) {
  return apiRequest<ActivityHealth>(`/api/activity/health?guild_id=${guildId}`, {}, token);
}

export function getWelcomeConfig(guildId: string, token: string) {
  return apiRequest<WelcomeConfig>(`/api/welcome/config?guild_id=${guildId}`, {}, token);
}

export function saveWelcomeConfig(config: WelcomeConfig, token: string) {
  return apiRequest<WelcomeConfig>("/api/welcome/config", {
    method: "PUT",
    body: JSON.stringify(config),
  }, token);
}

export function resetWelcomeConfig(guildId: string, token: string) {
  return apiRequest<WelcomeConfig>(`/api/welcome/config?guild_id=${guildId}`, {
    method: "DELETE",
  }, token);
}

export function getDiscordChannels(guildId: string, token: string, kind?: "text" | "voice") {
  const suffix = kind ? `&kind=${kind}` : "";
  return apiRequest<DiscordChannel[]>(`/api/discord/channels?guild_id=${guildId}${suffix}`, {}, token);
}

export function getDiscordRoles(guildId: string, token: string) {
  return apiRequest<DiscordRole[]>(`/api/discord/roles?guild_id=${guildId}`, {}, token);
}

export function searchDiscordMembers(guildId: string, token: string, query: string) {
  return apiRequest<DiscordMember[]>(`/api/discord/members/search?guild_id=${guildId}&q=${encodeURIComponent(query)}`, {}, token);
}

export function getChannelPurposes(guildId: string, token: string) {
  return apiRequest<Record<ChannelPurpose, number | undefined>>(`/api/activity/channel-purposes?guild_id=${guildId}`, {}, token);
}

export function saveChannelPurpose(guildId: string, token: string, purpose: ChannelPurpose, channelId: string) {
  return apiRequest<Record<ChannelPurpose, number | undefined>>("/api/activity/channel-purposes", {
    method: "PUT",
    body: JSON.stringify({ guild_id: Number(guildId), purpose, channel_id: Number(channelId) }),
  }, token);
}

export function getActivityRoles(guildId: string, token: string) {
  return apiRequest<Record<ActivityRolePurpose, number | undefined>>(`/api/activity/roles?guild_id=${guildId}`, {}, token);
}

export function saveActivityRole(guildId: string, token: string, purpose: ActivityRolePurpose, roleId: string) {
  return apiRequest<Record<ActivityRolePurpose, number | undefined>>("/api/activity/roles", {
    method: "PUT",
    body: JSON.stringify({ guild_id: Number(guildId), purpose, role_id: Number(roleId) }),
  }, token);
}

export function getDevBlogPosts(guildId: string, token: string) {
  return apiRequest<Array<Record<string, unknown>>>(`/api/dev-blog/posts?guild_id=${guildId}`, {}, token);
}

export function createDevBlogPost(draft: DevBlogDraft, token: string) {
  return apiRequest<Record<string, unknown>>("/api/dev-blog/posts", {
    method: "POST",
    body: JSON.stringify(draft),
  }, token);
}

export function getCreatorAlertSources(guildId: string, token: string) {
  return apiRequest<CreatorAlertSource[]>(`/api/creator-alerts/sources?guild_id=${guildId}`, {}, token);
}

export function saveCreatorAlertSource(source: CreatorAlertSource, token: string) {
  return apiRequest<Record<string, unknown>>("/api/creator-alerts/sources", {
    method: "PUT",
    body: JSON.stringify(source),
  }, token);
}

export function previewCreatorAlert(source: CreatorAlertSource, token: string) {
  return apiRequest<Record<string, unknown>>("/api/creator-alerts/test", {
    method: "POST",
    body: JSON.stringify({
      guild_id: source.guild_id,
      platform: source.platform,
      channel_name: source.channel_name || "Creator",
      channel_url: source.channel_url,
      template: source.template,
      ping_role_id: source.ping_role_id,
    }),
  }, token);
}

export function getVoiceRooms(guildId: string, token: string) {
  return apiRequest<VoiceRoom[]>(`/api/voice/rooms?guild_id=${guildId}`, {}, token);
}

export function updateVoiceRoom(guildId: string, token: string, channelId: number, payload: Record<string, unknown>) {
  return apiRequest<Record<string, unknown>>(`/api/voice/rooms/${channelId}`, {
    method: "PATCH",
    body: JSON.stringify({ guild_id: Number(guildId), ...payload }),
  }, token);
}

export function deleteVoiceRoom(guildId: string, token: string, channelId: number) {
  return apiRequest<Record<string, unknown>>(`/api/voice/rooms/${channelId}?guild_id=${guildId}`, {
    method: "DELETE",
  }, token);
}

export function getServerStats(guildId: string, token: string, period = 7) {
  return apiRequest<ServerStatsPayload>(`/api/stats/server?guild_id=${guildId}&period=${period}`, {}, token);
}

export function searchUserStats(guildId: string, token: string, query: string) {
  return apiRequest<Array<Record<string, unknown>>>(`/api/stats/users/search?guild_id=${guildId}&q=${encodeURIComponent(query)}`, {}, token);
}

export function getLogs(guildId: string, token: string, source = "all", eventType = "", query = "") {
  const params = new URLSearchParams({ guild_id: guildId, source, q: query });
  if (eventType) params.set("event_type", eventType);
  return apiRequest<LogsPayload>(`/api/logs?${params.toString()}`, {}, token);
}

export function getBotSettings(guildId: string, token: string) {
  return apiRequest<Record<string, unknown>>(`/api/bot/settings?guild_id=${guildId}`, {}, token);
}

export function getIntegrations(guildId: string, token: string) {
  return apiRequest<Record<string, unknown>>(`/api/integrations?guild_id=${guildId}`, {}, token);
}
