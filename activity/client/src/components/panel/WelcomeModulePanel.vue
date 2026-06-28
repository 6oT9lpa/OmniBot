<script setup lang="ts">
import { reactive, watch } from "vue";
import { useActivityStore } from "../../stores/activity.store";
import type { WelcomeConfig } from "../../types/activity.types";
import DiscordEmbedPreview from "./DiscordEmbedPreview.vue";

const activity = useActivityStore();
const welcomeDraft = reactive<WelcomeConfig>({ ...activity.welcome });
const saving = reactive({ value: false, message: "" });

watch(
  () => activity.welcome,
  (next) => Object.assign(welcomeDraft, next),
  { deep: true },
);

async function saveWelcome() {
  saving.value = true;
  saving.message = "Saving...";
  await activity.saveWelcome({ ...welcomeDraft });
  saving.value = false;
  saving.message = "Saved";
}

async function resetWelcome() {
  await activity.resetWelcome();
  Object.assign(welcomeDraft, activity.welcome);
  saving.message = "Reset complete";
}

async function testWelcome() {
  saving.value = true;
  saving.message = "Sending test...";
  try {
    await activity.testWelcome();
    saving.message = "Test message sent";
  } catch (error) {
    saving.message = error instanceof Error ? error.message : "Welcome channel is not configured";
  } finally {
    saving.value = false;
  }
}

function colorToHex(value: number) {
  return `#${value.toString(16).padStart(6, "0").slice(-6)}`;
}

function setColor(value: string) {
  welcomeDraft.color = parseInt(value.replace("#", ""), 16);
}
</script>

<template>
  <section class="editor-grid">
    <form class="control-surface" @submit.prevent="saveWelcome">
      <div class="section-heading">
        <span>Welcome Alerts</span>
        <h2>Design the first server moment.</h2>
      </div>

      <label class="toggle-row">
        <input v-model="welcomeDraft.is_enabled" type="checkbox" />
        <span>Enable welcome message</span>
      </label>

      <label>
        Title
        <input v-model="welcomeDraft.title" maxlength="256" />
      </label>

      <label>
        Description
        <textarea v-model="welcomeDraft.description" rows="7" maxlength="2000" />
      </label>

      <div class="form-grid">
        <label>
          Color
          <input type="color" :value="colorToHex(welcomeDraft.color)" @input="setColor(($event.target as HTMLInputElement).value)" />
        </label>
        <label>
          Rules channel
          <select v-model="welcomeDraft.rules_channel_id">
            <option :value="null">Not selected</option>
            <option v-for="channel in activity.textChannels" :key="channel.id" :value="channel.id">
              #{{ channel.name }}
            </option>
          </select>
        </label>
        <label>
          Roles channel
          <select v-model="welcomeDraft.roles_channel_id">
            <option :value="null">Not selected</option>
            <option v-for="channel in activity.textChannels" :key="channel.id" :value="channel.id">
              #{{ channel.name }}
            </option>
          </select>
        </label>
        <label>
          Footer
          <input v-model="welcomeDraft.footer_text" placeholder="OmniBot Activity" />
        </label>
      </div>

      <div class="variable-row">
        <span>{user}</span>
        <span>{server}</span>
        <span>{member_count}</span>
        <span>{joined_at}</span>
      </div>

      <div class="form-actions">
        <button class="primary-button" type="submit" :disabled="saving.value">Save</button>
        <button class="ghost-button" type="button" @click="resetWelcome">Reset</button>
        <button class="ghost-button" type="button" :disabled="saving.value" @click="testWelcome">Test</button>
        <small>{{ saving.message }}</small>
      </div>
    </form>

    <DiscordEmbedPreview :config="welcomeDraft" />
  </section>
</template>
