import { apiRequest } from "./client";
import type { ActivityHealth, ActivitySession, TokenResponse, WelcomeConfig } from "../types/activity.types";

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
