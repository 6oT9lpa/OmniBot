<script setup lang="ts">
import { computed, ref } from "vue";
import { RefreshCcw } from "@lucide/vue";
import RevealOnScroll from "../common/RevealOnScroll.vue";
import { useActivityStore } from "../../stores/activity.store";
import type { ActivityRolePurpose, ChannelPurpose } from "../../types/activity.types";
import { t } from "../../i18n";

type BotSettingsTab = "general" | "channels" | "roles";

const activity = useActivityStore();
const activeTab = ref<BotSettingsTab>("general");
const status = ref("");
const tabs = computed<Array<{ key: BotSettingsTab; label: string }>>(() => ["general", "channels", "roles"].map((key) => ({ key: key as BotSettingsTab, label: t(`settings.${key}`) })));
const channelPurposeKeys: ChannelPurpose[] = ["welcome", "member_log", "mod_log", "message_log", "channel_log", "stream_announce", "dev_blog", "ai_moderation_log"];
const channelPurposes = computed(() => channelPurposeKeys.map((key) => ({ key, label: t(`settings.channel.${key}`) })));
const rolePurposeKeys: ActivityRolePurpose[] = ["activity_admin", "activity_streamer", "activity_developer", "ping_stream", "ping_dev"];
const rolePurposes = computed(() => rolePurposeKeys.map((key) => ({ key, label: t(`settings.role.${key}`) })));
const subscriptionTier = computed(() => activity.botSettings?.subscription_tier || "free");
const runtimeRows = computed(() => [
  [t("settings.presence_rotation"), t(activity.botSettings?.activity_rotation_enabled ? "common.enabled" : "common.disabled")],
  [t("settings.rotation_interval"), t("settings.seconds", { value: activity.botSettings?.activity_rotation_interval_seconds || "-" })],
  [t("settings.message_retention"), t("settings.days", { value: activity.botSettings?.retention?.message_log_retention_days || "-" })],
  [t("settings.punishment_retention"), t("settings.days", { value: activity.botSettings?.retention?.punishment_retention_days || "-" })],
]);

async function saveChannel(purpose: ChannelPurpose, value: string) {
  if (!value) return;
  try {
    await activity.saveChannelPurposeValue(purpose, value);
    status.value = t("settings.channel_saved");
  } catch {
    status.value = t("settings.channel_failed");
  }
}

async function saveRole(purpose: ActivityRolePurpose, value: string) {
  if (!value) return;
  try {
    await activity.saveActivityRolePurpose(purpose, value);
    status.value = t("settings.role_saved");
  } catch {
    status.value = t("settings.role_failed");
  }
}

async function toggleWelcome(value: boolean) {
  try {
    await activity.saveWelcome({ ...activity.welcome, is_enabled: value });
    status.value = t("settings.welcome_saved");
  } catch {
    status.value = t("settings.welcome_failed");
  }
}
</script>

<template>
  <RevealOnScroll tag="section" class="panel-section ai-moderation-hero">
    <div class="section-heading bot-settings-heading">
      <span>{{ $t("module.bot-settings") }}</span>
      <h2>{{ $t("settings.heading") }}</h2>
      <div><p>{{ $t("settings.description") }}</p></div>
      <button class="ghost-button" type="button" :disabled="activity.moduleLoading" @click="activity.syncRolesFromDiscord">
        <RefreshCcw :size="16" /> {{ $t("settings.sync_roles") }}
      </button>
    </div>
    <nav class="ai-moderation-nav" :aria-label="$t('module.bot-settings')">
      <button v-for="tab in tabs" :key="tab.key" type="button" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</button>
    </nav>
  </RevealOnScroll>

  <RevealOnScroll tag="section" class="panel-section" :delay="60">
    <div v-if="activeTab === 'general'" class="settings-list">
      <article>
        <strong>{{ $t("settings.subscription") }}</strong>
        <span :class="['subscription-tier', subscriptionTier]">{{ subscriptionTier }}</span>
        <small>{{ $t("settings.plans") }}</small>
      </article>
      <article>
        <strong>{{ $t("settings.welcome_toggle") }}</strong>
        <label class="toggle-row">
          <input type="checkbox" :checked="activity.welcome.is_enabled" @change="toggleWelcome(($event.target as HTMLInputElement).checked)" />
          <span>{{ $t(activity.welcome.is_enabled ? "common.enabled" : "common.disabled") }}</span>
        </label>
      </article>
      <article v-for="[label, value] in runtimeRows" :key="label"><strong>{{ label }}</strong><span>{{ value }}</span></article>
    </div>

    <div v-else-if="activeTab === 'channels'" class="settings-list">
      <article v-for="purpose in channelPurposes" :key="purpose.key">
        <strong>{{ purpose.label }}</strong>
        <!-- v-model preserves each select's independent displayed snowflake after a reactive refresh. -->
        <select v-model="activity.channelPurposes[purpose.key]" @change="saveChannel(purpose.key, activity.channelPurposes[purpose.key] || '')">
          <option value="">{{ $t("settings.select_channel") }}</option>
          <option v-for="channel in activity.textChannels" :key="channel.id" :value="channel.id">#{{ channel.name }}</option>
        </select>
      </article>
      <article v-if="activity.textChannels.length === 0"><strong>{{ $t("settings.no_channels") }}</strong><span>{{ $t("settings.no_channels_text") }}</span></article>
    </div>

    <div v-else class="settings-list">
      <article v-for="purpose in rolePurposes" :key="purpose.key">
        <strong>{{ purpose.label }}</strong>
        <select v-model="activity.activityRoles[purpose.key]" @change="saveRole(purpose.key, activity.activityRoles[purpose.key] || '')">
          <option value="">{{ $t("settings.select_role") }}</option>
          <option v-for="role in activity.roles" :key="role.id" :value="role.id">{{ role.name }}</option>
        </select>
      </article>
      <article v-if="activity.roles.length === 0"><strong>{{ $t("settings.no_roles") }}</strong><span>{{ $t("settings.no_roles_text") }}</span></article>
    </div>
    <small v-if="status" class="ai-moderation-status" role="status">{{ status }}</small>
  </RevealOnScroll>
</template>
