<script setup lang="ts">
import { reactive } from "vue";
import StatusBadge from "../common/StatusBadge.vue";
import { useActivityStore } from "../../stores/activity.store";

const activity = useActivityStore();
const creatorDraft = reactive({
  platform: "twitch" as "twitch" | "youtube" | "kick",
  channel_url: "",
  channel_name: "",
  template: "{creator} is active on {platform}: {url}",
  ping_role_id: null as string | null,
  active: true,
});
const saving = reactive({ value: false, message: "" });

async function saveCreator() {
  saving.value = true;
  saving.message = "Saving source...";
  await activity.saveCreatorSource(creatorDraft);
  saving.value = false;
  saving.message = "Source saved";
}

async function previewCreator() {
  await activity.previewCreatorSource(creatorDraft);
}

function roleName(id: unknown) {
  const value = String(id ?? "");
  return activity.roles.find((role) => role.id === value)?.name || value || "No role";
}

function formatRecordValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
</script>

<template>
  <section class="editor-grid">
    <form class="control-surface" @submit.prevent="saveCreator">
      <div class="section-heading">
        <span>Creator workspace</span>
        <h2>Sources, templates and notification history.</h2>
        <p>Creators see their own sources. Administrators can manage every creator.</p>
      </div>
      <div class="form-grid">
        <label>
          Platform
          <select v-model="creatorDraft.platform">
            <option value="twitch">Twitch</option>
            <option value="youtube">YouTube</option>
            <option value="kick">Kick</option>
          </select>
        </label>
        <label>
          Ping role
          <select
            :value="creatorDraft.ping_role_id || ''"
            @change="creatorDraft.ping_role_id = ($event.target as HTMLSelectElement).value || null"
          >
            <option value="">No ping</option>
            <option v-for="role in activity.roles" :key="role.id" :value="role.id">@{{ role.name }}</option>
          </select>
        </label>
      </div>
      <label>
        Channel name
        <input v-model="creatorDraft.channel_name" maxlength="120" placeholder="Creator name" />
      </label>
      <label>
        Platform URL
        <input v-model="creatorDraft.channel_url" maxlength="2048" placeholder="https://..." />
      </label>
      <label>
        Alert template
        <textarea v-model="creatorDraft.template" rows="5" maxlength="2000" />
      </label>
      <label class="toggle-row">
        <input v-model="creatorDraft.active" type="checkbox" />
        <span>Active source</span>
      </label>
      <div class="variable-row">
        <span>{creator}</span>
        <span>{platform}</span>
        <span>{url}</span>
      </div>
      <div class="form-actions">
        <button class="primary-button" type="submit" :disabled="saving.value">Save source</button>
        <button class="ghost-button" type="button" @click="previewCreator">Preview test</button>
        <small>{{ saving.message }}</small>
      </div>
    </form>

    <article class="discord-preview">
      <div class="discord-preview-header"><span>Creator alert preview</span><strong>Test</strong></div>
      <h3>{{ creatorDraft.channel_name || "Creator" }}</h3>
      <p>{{ activity.creatorPreview ? formatRecordValue(activity.creatorPreview) : "Preview appears after test." }}</p>
      <footer>
        <span>{{ creatorDraft.platform }}</span>
        <span>{{ roleName(creatorDraft.ping_role_id) }}</span>
      </footer>
    </article>
  </section>
  <section class="panel-section">
    <div class="section-heading">
      <span>Saved sources</span>
      <h2>{{ activity.creatorSources.length }} connected creator sources.</h2>
    </div>
    <div class="source-list">
      <article v-for="source in activity.creatorSources" :key="`${source.user_id}-${source.platform}`">
        <strong>{{ source.channel_name || source.platform }}</strong>
        <span>{{ source.channel_url }}</span>
        <StatusBadge :label="source.active ? 'active' : 'paused'" :tone="source.active ? 'success' : 'warning'" />
      </article>
    </div>
  </section>
</template>
