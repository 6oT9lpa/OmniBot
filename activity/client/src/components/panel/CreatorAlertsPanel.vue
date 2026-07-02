<script setup lang="ts">
import { computed, reactive } from "vue";
import StatusBadge from "../common/StatusBadge.vue";
import { useActivityStore } from "../../stores/activity.store";
import type { CreatorAlertSource } from "../../types/activity.types";

const activity = useActivityStore();
const creatorDraft = reactive<CreatorAlertSource>({
  platform: "twitch",
  alert_kind: "stream",
  channel_url: "",
  channel_name: "",
  external_channel_id: "",
  title_template: "{creator.name} начал стрим на {platform}",
  description_template: "{creator.ping}\n\n**{creator.name} уже в эфире.**\n\n**Название:** {title}\n**Категория:** {game}\n\n{url}",
  button_label: "Watch",
  color: 0x5865F2,
  ping_role_id: null,
  active: true,
  guild_id: "",
});
const saving = reactive({ value: false, message: "" });
const sourceLimitReached = computed(() => activity.creatorSources.length >= 5 && !creatorDraft.id);

async function saveCreator() {
  saving.value = true;
  saving.message = "Saving source...";
  try {
    await activity.saveCreatorSource(creatorDraft);
    resetDraft();
    saving.message = "Source saved";
  } catch (error) {
    saving.message = error instanceof Error ? error.message : String(error);
  } finally {
    saving.value = false;
  }
}

async function previewCreator() {
  try {
    await activity.previewCreatorSource(creatorDraft);
    saving.message = "Preview ready";
  } catch (error) {
    saving.message = error instanceof Error ? error.message : String(error);
  }
}

async function deleteCreator(source: CreatorAlertSource) {
  if (!source.id) return;
  try {
    await activity.deleteCreatorSource(source.id);
    saving.message = "Source removed";
  } catch (error) {
    saving.message = error instanceof Error ? error.message : String(error);
  }
}

function editCreator(source: CreatorAlertSource) {
  Object.assign(creatorDraft, {
    ...source,
    ping_role_id: source.ping_role_id || null,
    color: source.color ?? 0x5865F2,
    button_label: source.button_label || "Watch",
  });
}

function resetDraft() {
  Object.assign(creatorDraft, {
    id: undefined,
    platform: "twitch",
    alert_kind: "stream",
    channel_url: "",
    channel_name: "",
    external_channel_id: "",
    title_template: "{creator.name} начал стрим на {platform}",
    description_template: "{creator.ping}\n\n**{creator.name} уже в эфире.**\n\n**Название:** {title}\n**Категория:** {game}\n\n{url}",
    button_label: "Watch",
    color: 0x5865F2,
    ping_role_id: null,
    active: true,
  });
}

function roleName(id: unknown) {
  const value = String(id ?? "");
  return activity.roles.find((role) => role.id === value)?.name || value || "Default stream ping";
}

function formatRecordValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}
</script>

<template>
  <section class="editor-grid">
    <form class="control-surface" @submit.prevent="saveCreator">
      <div class="section-heading">
        <span>Creator workspace</span>
        <h2>Sources, templates and notification history.</h2>
        <div>
          <p>{{ activity.creatorSources.length }} / 5 connected sources.</p>
        </div>
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
          Alert kind
          <select v-model="creatorDraft.alert_kind">
            <option value="stream">Stream</option>
            <option value="video">Video</option>
            <option value="short">Short</option>
          </select>
        </label>
        <label>
          Ping role
          <select
            :value="creatorDraft.ping_role_id || ''"
            @change="creatorDraft.ping_role_id = ($event.target as HTMLSelectElement).value || null"
          >
            <option value="">Default stream ping</option>
            <option v-for="role in activity.roles" :key="role.id" :value="role.id">@{{ role.name }}</option>
          </select>
        </label>
        <label>
          Embed color
          <input
            type="color"
            :value="`#${Number(creatorDraft.color || 0x5865F2).toString(16).padStart(6, '0')}`"
            @input="creatorDraft.color = parseInt(($event.target as HTMLInputElement).value.slice(1), 16)"
          />
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
        External channel ID
        <input v-model="creatorDraft.external_channel_id" maxlength="160" placeholder="Optional Twitch login or YouTube channel ID" />
      </label>
      <label>
        Embed title
        <input v-model="creatorDraft.title_template" maxlength="256" />
      </label>
      <label>
        Embed description
        <textarea v-model="creatorDraft.description_template" rows="5" maxlength="2000" />
      </label>
      <label>
        Button label
        <input v-model="creatorDraft.button_label" maxlength="80" />
      </label>
      <label class="toggle-row">
        <input v-model="creatorDraft.active" type="checkbox" />
        <span>Active source</span>
      </label>
      <div class="variable-row">
        <span>{creator.name}</span>
        <span>{creator.ping}</span>
        <span>{platform}</span>
        <span>{url}</span>
        <span>{game}</span>
        <span>{title}</span>
      </div>
      <div class="form-actions">
        <button class="primary-button" type="submit" :disabled="saving.value || sourceLimitReached">Save source</button>
        <button class="ghost-button" type="button" @click="previewCreator">Preview test</button>
        <button class="ghost-button" type="button" @click="resetDraft">New</button>
        <small>{{ sourceLimitReached ? "Source limit reached" : saving.message }}</small>
      </div>
    </form>

    <article class="discord-preview">
      <div class="discord-preview-header"><span>Creator alert preview</span><strong>Test</strong></div>
      <h3>{{ creatorDraft.channel_name || "Creator" }}</h3>
      <pre>{{ activity.creatorPreview ? formatRecordValue(activity.creatorPreview) : "Preview appears after test." }}</pre>
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
      <article v-for="source in activity.creatorSources" :key="source.id || `${source.user_id}-${source.platform}-${source.channel_url}`">
        <strong>{{ source.channel_name || source.platform }}</strong>
        <span>{{ source.platform }} / {{ source.alert_kind || "stream" }}</span>
        <span>{{ source.channel_url }}</span>
        <StatusBadge :label="source.active ? 'active' : 'paused'" :tone="source.active ? 'success' : 'warning'" />
        <div class="form-actions">
          <button class="ghost-button" type="button" @click="editCreator(source)">Edit</button>
          <button class="ghost-button" type="button" @click="deleteCreator(source)">Delete</button>
        </div>
      </article>
    </div>
  </section>
</template>
