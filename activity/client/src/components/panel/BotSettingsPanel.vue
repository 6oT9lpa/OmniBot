<script setup lang="ts">
import { computed, reactive } from "vue";
import { RefreshCcw } from "@lucide/vue";
import RevealOnScroll from "../common/RevealOnScroll.vue";
import { useActivityStore } from "../../stores/activity.store";
import type { ActivityRolePurpose, ChannelPurpose } from "../../types/activity.types";

const activity = useActivityStore();
const status = reactive({ message: "" });
const channelPurposes: Array<{ key: ChannelPurpose; label: string }> = [
  { key: "welcome", label: "Welcome" },
  { key: "member_log", label: "Log welcome" },
  { key: "mod_log", label: "Log moderator" },
  { key: "message_log", label: "Log message" },
  { key: "channel_log", label: "Log channel" },
  { key: "stream_announce", label: "Stream alerts" },
  { key: "dev_blog", label: "Dev Blog" },
];
const rolePurposes: Array<{ key: ActivityRolePurpose; label: string }> = [
  { key: "activity_admin", label: "Activity admin" },
  { key: "activity_streamer", label: "Activity creator" },
  { key: "activity_developer", label: "Activity developer" },
  { key: "ping_stream", label: "Ping stream" },
  { key: "ping_dev", label: "Ping Dev Blog" },
];
const runtimeRows = computed(() => {
  return [
    ["command_prefix", activity.botSettings?.command_prefix],
    ["activity_name", activity.botSettings?.activity_name],
    ["bot_status", activity.botSettings?.bot_status],
    ["log_level", activity.botSettings?.log_level],
  ];
});

async function saveChannel(purpose: ChannelPurpose, value: string) {
  if (!value) return;
  await activity.saveChannelPurposeValue(purpose, value);
  status.message = "Channel saved";
}

async function saveRole(purpose: ActivityRolePurpose, value: string) {
  if (!value) return;
  await activity.saveActivityRolePurpose(purpose, value);
  status.message = "Role saved";
}

async function toggleWelcome(value: boolean) {
  await activity.saveWelcome({ ...activity.welcome, is_enabled: value });
  status.message = "Welcome toggle saved";
}
</script>

<template>
  <RevealOnScroll tag="section" class="panel-section">
    <div class="section-heading bot-settings-heading">
      <span>Bot settings</span>
      <h2>Discord bot controls.</h2>
      <div>
        <p>Review runtime values and keep the global welcome toggle in one place.</p>
      </div>
      <button class="ghost-button" type="button" :disabled="activity.moduleLoading" @click="activity.syncRolesFromDiscord">
        <RefreshCcw :size="16" />
        Sync roles
      </button>
    </div>

    <div class="settings-list">
      <article>
        <strong>Welcome toggle</strong>
        <label class="toggle-row">
          <input
            type="checkbox"
            :checked="activity.welcome.is_enabled"
            @change="toggleWelcome(($event.target as HTMLInputElement).checked)"
          />
          <span>{{ activity.welcome.is_enabled ? "enabled" : "disabled" }}</span>
        </label>
      </article>
      <article v-for="[key, value] in runtimeRows" :key="key">
        <strong>{{ key }}</strong>
        <span>{{ value || "-" }}</span>
      </article>
    </div>
  </RevealOnScroll>

  <RevealOnScroll tag="section" class="panel-section" :delay="80">
    <div class="section-heading">
      <span>List channels</span>
      <h2>Set channel commands.</h2>
      <div>
        <p>Route welcome, logs, stream alerts and Dev Blog messages to the right Discord channels.</p>
      </div>
    </div>
    <div class="settings-list">
      <article v-for="purpose in channelPurposes" :key="purpose.key">
        <strong>{{ purpose.label }}</strong>
        <select
          :value="activity.channelPurposes[purpose.key] || ''"
          @change="saveChannel(purpose.key, ($event.target as HTMLSelectElement).value)"
        >
          <option value="">Select channel</option>
          <option v-for="channel in activity.textChannels" :key="channel.id" :value="channel.id">#{{ channel.name }}</option>
        </select>
      </article>
      <article v-if="activity.textChannels.length === 0">
        <strong>No channels loaded</strong>
        <span>Discord did not return text channels for this server.</span>
      </article>
    </div>
  </RevealOnScroll>

  <RevealOnScroll tag="section" class="panel-section" :delay="120">
    <div class="section-heading">
      <span>List roles</span>
      <h2>Set role commands.</h2>
      <div>
        <p>Map Discord roles to Activity access and default publication pings.</p>
      </div>
    </div>
    <div class="settings-list">
      <article v-for="purpose in rolePurposes" :key="purpose.key">
        <strong>{{ purpose.label }}</strong>
        <select
          :value="activity.activityRoles[purpose.key] || ''"
          @change="saveRole(purpose.key, ($event.target as HTMLSelectElement).value)"
        >
          <option value="">Select role</option>
          <option v-for="role in activity.roles" :key="role.id" :value="role.id">{{ role.name }}</option>
        </select>
      </article>
      <article v-if="activity.roles.length === 0">
        <strong>No roles loaded</strong>
        <span>Discord did not return roles for this server.</span>
      </article>
    </div>
    <small>{{ status.message }}</small>
  </RevealOnScroll>
</template>
