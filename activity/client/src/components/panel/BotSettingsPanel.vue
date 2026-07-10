<script setup lang="ts">
import { computed, ref } from "vue";
import { RefreshCcw } from "@lucide/vue";
import RevealOnScroll from "../common/RevealOnScroll.vue";
import { useActivityStore } from "../../stores/activity.store";
import type { ActivityRolePurpose, ChannelPurpose } from "../../types/activity.types";

type BotSettingsTab = "general" | "channels" | "roles";

const activity = useActivityStore();
const activeTab = ref<BotSettingsTab>("general");
const status = ref("");
const tabs: Array<{ key: BotSettingsTab; label: string }> = [
  { key: "general", label: "General" },
  { key: "channels", label: "Channels" },
  { key: "roles", label: "Roles" },
];
const channelPurposes: Array<{ key: ChannelPurpose; label: string }> = [
  { key: "welcome", label: "Welcome" },
  { key: "member_log", label: "Log welcome" },
  { key: "mod_log", label: "Log moderator" },
  { key: "message_log", label: "Log message" },
  { key: "channel_log", label: "Log channel" },
  { key: "stream_announce", label: "Stream alerts" },
  { key: "dev_blog", label: "Dev Blog" },
  { key: "ai_moderation_log", label: "AI moderation log" },
];
const rolePurposes: Array<{ key: ActivityRolePurpose; label: string }> = [
  { key: "activity_admin", label: "Activity admin" },
  { key: "activity_streamer", label: "Activity creator" },
  { key: "activity_developer", label: "Activity developer" },
  { key: "ping_stream", label: "Ping stream" },
  { key: "ping_dev", label: "Ping Dev Blog" },
];
const subscriptionTier = computed(() => activity.botSettings?.subscription_tier || "free");
const runtimeRows = computed(() => [
  ["Presence rotation", activity.botSettings?.activity_rotation_enabled ? "Enabled" : "Disabled"],
  ["Rotation interval", `${activity.botSettings?.activity_rotation_interval_seconds || "-"} seconds`],
  ["Message-log retention", `${activity.botSettings?.retention?.message_log_retention_days || "-"} days`],
  ["Punishment retention", `${activity.botSettings?.retention?.punishment_retention_days || "-"} days`],
]);

async function saveChannel(purpose: ChannelPurpose, value: string) {
  if (!value) return;
  try {
    await activity.saveChannelPurposeValue(purpose, value);
    status.value = "Channel assignment saved.";
  } catch {
    status.value = "Could not save the channel assignment.";
  }
}

async function saveRole(purpose: ActivityRolePurpose, value: string) {
  if (!value) return;
  try {
    await activity.saveActivityRolePurpose(purpose, value);
    status.value = "Role assignment saved.";
  } catch {
    status.value = "Could not save the role assignment.";
  }
}

async function toggleWelcome(value: boolean) {
  try {
    await activity.saveWelcome({ ...activity.welcome, is_enabled: value });
    status.value = "Welcome setting saved.";
  } catch {
    status.value = "Could not save the welcome setting.";
  }
}
</script>

<template>
  <RevealOnScroll tag="section" class="panel-section ai-moderation-hero">
    <div class="section-heading bot-settings-heading">
      <span>Bot settings</span>
      <h2>Organize the server configuration.</h2>
      <div><p>Manage general controls, message destinations, and Discord role mappings in separate sections.</p></div>
      <button class="ghost-button" type="button" :disabled="activity.moduleLoading" @click="activity.syncRolesFromDiscord">
        <RefreshCcw :size="16" /> Sync roles
      </button>
    </div>
    <nav class="ai-moderation-nav" aria-label="Bot settings">
      <button v-for="tab in tabs" :key="tab.key" type="button" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</button>
    </nav>
  </RevealOnScroll>

  <RevealOnScroll tag="section" class="panel-section" :delay="60">
    <div v-if="activeTab === 'general'" class="settings-list">
      <article>
        <strong>Subscription</strong>
        <span :class="['subscription-tier', subscriptionTier]">{{ subscriptionTier }}</span>
        <small>Available plans: Free, Plus, Pro.</small>
      </article>
      <article>
        <strong>Welcome toggle</strong>
        <label class="toggle-row">
          <input type="checkbox" :checked="activity.welcome.is_enabled" @change="toggleWelcome(($event.target as HTMLInputElement).checked)" />
          <span>{{ activity.welcome.is_enabled ? "enabled" : "disabled" }}</span>
        </label>
      </article>
      <article v-for="[label, value] in runtimeRows" :key="label"><strong>{{ label }}</strong><span>{{ value }}</span></article>
    </div>

    <div v-else-if="activeTab === 'channels'" class="settings-list">
      <article v-for="purpose in channelPurposes" :key="purpose.key">
        <strong>{{ purpose.label }}</strong>
        <!-- v-model preserves each select's independent displayed snowflake after a reactive refresh. -->
        <select v-model="activity.channelPurposes[purpose.key]" @change="saveChannel(purpose.key, activity.channelPurposes[purpose.key] || '')">
          <option value="">Select channel</option>
          <option v-for="channel in activity.textChannels" :key="channel.id" :value="channel.id">#{{ channel.name }}</option>
        </select>
      </article>
      <article v-if="activity.textChannels.length === 0"><strong>No channels loaded</strong><span>Discord did not return text channels for this server.</span></article>
    </div>

    <div v-else class="settings-list">
      <article v-for="purpose in rolePurposes" :key="purpose.key">
        <strong>{{ purpose.label }}</strong>
        <select v-model="activity.activityRoles[purpose.key]" @change="saveRole(purpose.key, activity.activityRoles[purpose.key] || '')">
          <option value="">Select role</option>
          <option v-for="role in activity.roles" :key="role.id" :value="role.id">{{ role.name }}</option>
        </select>
      </article>
      <article v-if="activity.roles.length === 0"><strong>No roles loaded</strong><span>Discord did not return roles for this server.</span></article>
    </div>
    <small v-if="status" class="ai-moderation-status" role="status">{{ status }}</small>
  </RevealOnScroll>
</template>
