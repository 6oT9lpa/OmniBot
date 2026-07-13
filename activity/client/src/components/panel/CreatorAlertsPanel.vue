<script setup lang="ts">
import { computed, reactive } from "vue";
import { ExternalLink, Pencil, Trash2 } from "@lucide/vue";
import StatusBadge from "../common/StatusBadge.vue";
import { useActivityStore } from "../../stores/activity.store";
import type { CreatorAlertSource } from "../../types/activity.types";
import { t } from "../../i18n";

const activity = useActivityStore();
const DEFAULT_BUTTON_LABEL = "Watch";

const creatorDraft = reactive<CreatorAlertSource>({
  platform: "twitch",
  alert_kind: "stream",
  channel_url: "",
  channel_name: "",
  external_channel_id: "",
  title_template: "",
  description_template: "",
  button_label: DEFAULT_BUTTON_LABEL,
  color: 0x5865F2,
  ping_role_id: null,
  active: true,
  guild_id: "",
});
const saving = reactive({ value: false, message: "" });
const sourceLimitReached = computed(() => !activity.isAdmin && activity.creatorSources.length >= 5 && !creatorDraft.id);
const canManagePingRole = computed(() => activity.isAdmin);
const previewPayload = computed(() => activity.creatorPreview as Record<string, any> | null);
const previewEmbed = computed(() => previewPayload.value?.embeds?.[0] || null);
const previewButton = computed(() => previewPayload.value?.components?.[0]?.components?.[0] || null);

async function saveCreator() {
  saving.value = true;
  saving.message = t("creator.saving");
  try {
    await activity.saveCreatorSource(creatorDraft);
    resetDraft();
    saving.message = t("creator.source_saved");
  } catch (error) {
    saving.message = error instanceof Error ? error.message : String(error);
  } finally {
    saving.value = false;
  }
}

async function previewCreator() {
  try {
    await activity.previewCreatorSource(creatorDraft);
    saving.message = t("creator.preview_ready");
  } catch (error) {
    saving.message = error instanceof Error ? error.message : String(error);
  }
}

async function deleteCreator(source: CreatorAlertSource) {
  const sourceId = Number(source.id);
  if (!Number.isFinite(sourceId) || sourceId <= 0) {
    saving.message = t("creator.id_missing");
    return;
  }
  saving.value = true;
  saving.message = t("creator.removing");
  try {
    await activity.deleteCreatorSource(sourceId);
    saving.message = t("creator.removed");
  } catch (error) {
    saving.message = error instanceof Error ? error.message : String(error);
  } finally {
    saving.value = false;
  }
}

function editCreator(source: CreatorAlertSource) {
  Object.assign(creatorDraft, {
    ...source,
    ping_role_id: source.ping_role_id || null,
    color: source.color ?? 0x5865F2,
    button_label: source.button_label || DEFAULT_BUTTON_LABEL,
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
    title_template: "",
    description_template: "",
    button_label: DEFAULT_BUTTON_LABEL,
    color: 0x5865F2,
    ping_role_id: null,
    active: true,
  });
}

function roleName(id: unknown) {
  const value = String(id ?? "");
  return activity.roles.find((role) => role.id === value)?.name || value || t("creator.default_ping");
}

function platformLabel(platform: string | undefined | null) {
  return {
    twitch: "Twitch",
    youtube: "YouTube",
    kick: "Kick",
  }[platform || ""] || platform || t("creator.platform_fallback");
}

function hexColor(color: number | undefined | null) {
  return `#${Number(color ?? 0x5865F2).toString(16).padStart(6, "0").slice(-6)}`;
}

function previewContent() {
  return previewPayload.value?.content || "";
}

function fieldValue(index: number) {
  return previewEmbed.value?.fields?.[index]?.value || "-";
}
</script>

<template>
  <section class="editor-grid creator-alerts-grid">
    <form class="control-surface" @submit.prevent="saveCreator">
      <div class="section-heading">
        <span>{{ $t("creator.workspace") }}</span>
        <h2>{{ $t("creator.heading") }}</h2>
        <div>
          <p>{{ $t("creator.connected_count", { count: activity.creatorSources.length }) }}</p>
        </div>
      </div>
      <div class="form-grid">
        <label>
          {{ $t("creator.platform") }}
          <select v-model="creatorDraft.platform">
            <option value="twitch">Twitch</option>
            <option value="youtube">YouTube</option>
            <option value="kick">Kick</option>
          </select>
        </label>
        <label>
          {{ $t("creator.alert_kind") }}
          <select v-model="creatorDraft.alert_kind">
            <option value="stream">{{ $t("creator.stream") }}</option>
            <option value="video">{{ $t("creator.video") }}</option>
            <option value="short">{{ $t("creator.short") }}</option>
          </select>
        </label>
        <label>
          {{ $t("creator.ping_role") }}
          <select
            v-if="canManagePingRole"
            :value="creatorDraft.ping_role_id || ''"
            @change="creatorDraft.ping_role_id = ($event.target as HTMLSelectElement).value || null"
          >
            <option value="">{{ $t("creator.default_ping") }}</option>
            <option v-for="role in activity.roles" :key="role.id" :value="role.id">@{{ role.name }}</option>
          </select>
          <span v-else class="readonly-value">{{ roleName(creatorDraft.ping_role_id) }}</span>
        </label>
        <label>
          {{ $t("creator.embed_color") }}
          <input
            type="color"
            :value="hexColor(creatorDraft.color)"
            @input="creatorDraft.color = parseInt(($event.target as HTMLInputElement).value.slice(1), 16)"
          />
        </label>
      </div>
      <label>
        {{ $t("creator.channel_name") }}
        <input v-model="creatorDraft.channel_name" maxlength="120" :placeholder="$t('creator.creator_name')" />
      </label>
      <label>
        {{ $t("creator.platform_url") }}
        <input v-model="creatorDraft.channel_url" maxlength="2048" placeholder="https://..." />
      </label>
      <label>
        {{ $t("creator.external_id") }}
        <input v-model="creatorDraft.external_channel_id" maxlength="160" :placeholder="$t('creator.external_id_placeholder')" />
        <small>{{ $t("creator.external_id_help") }}</small>
      </label>
      <label>
        {{ $t("creator.embed_title") }}
        <input v-model="creatorDraft.title_template" maxlength="256" :placeholder="$t('creator.platform_default')" />
      </label>
      <label>
        {{ $t("creator.embed_description") }}
        <textarea v-model="creatorDraft.description_template" rows="5" maxlength="2000" :placeholder="$t('creator.platform_default')" />
      </label>
      <label>
        {{ $t("creator.button_label") }}
        <input v-model="creatorDraft.button_label" maxlength="80" />
      </label>
      <label class="toggle-row">
        <input v-model="creatorDraft.active" type="checkbox" />
        <span>{{ $t("creator.active_source") }}</span>
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
        <button class="primary-button" type="submit" :disabled="saving.value || sourceLimitReached">{{ $t("creator.save_source") }}</button>
        <button class="ghost-button" type="button" @click="previewCreator">{{ $t("creator.preview_test") }}</button>
        <button class="ghost-button" type="button" @click="resetDraft">{{ $t("creator.new") }}</button>
        <small>{{ sourceLimitReached ? $t("creator.limit_reached") : saving.message }}</small>
      </div>
    </form>

    <article class="discord-preview creator-preview" :style="{ borderLeftColor: hexColor(previewEmbed?.color ?? creatorDraft.color) }">
      <div class="discord-preview-header"><span>{{ $t("creator.preview_heading") }}</span><strong>{{ $t("common.test") }}</strong></div>
      <template v-if="previewEmbed">
        <p v-if="previewContent()" class="preview-content">{{ previewContent() }}</p>
        <h3>{{ previewEmbed.title }}</h3>
        <p>{{ previewEmbed.description }}</p>
        <div class="preview-fields">
          <span><strong>{{ $t("creator.platform") }}</strong>{{ fieldValue(0) }}</span>
          <span><strong>{{ $t("creator.category") }}</strong>{{ fieldValue(1) }}</span>
        </div>
        <div v-if="previewEmbed.image?.url" class="preview-image">
          <img :src="previewEmbed.image.url" alt="" />
        </div>
        <a v-if="previewButton" class="stream-link-button" :href="previewButton.url" target="_blank" rel="noreferrer">
          <ExternalLink :size="16" />
          {{ previewButton.label }}
        </a>
      </template>
      <p v-else>{{ $t("creator.preview_empty") }}</p>
      <footer>
        <span>{{ platformLabel(creatorDraft.platform) }}</span>
        <span>{{ roleName(creatorDraft.ping_role_id) }}</span>
      </footer>
    </article>
  </section>
  <section class="panel-section">
    <div class="section-heading">
      <span>{{ $t("creator.saved_sources") }}</span>
      <h2>{{ $t("creator.connected_sources", { count: activity.creatorSources.length }) }}</h2>
      <p>{{ $t(activity.isAdmin ? "creator.admin_view" : "creator.own_view") }}</p>
    </div>
    <div class="source-list creator-source-list">
      <article v-for="source in activity.creatorSources" :key="source.id || `${source.user_id}-${source.platform}-${source.channel_url}`">
        <header>
          <div>
            <strong>{{ source.channel_name || platformLabel(source.platform) }}</strong>
            <span>{{ platformLabel(source.platform) }} / {{ $t(`creator.${source.alert_kind || 'stream'}`) }}</span>
          </div>
          <StatusBadge :label="$t(source.active ? 'creator.active' : 'creator.paused')" :tone="source.active ? 'success' : 'warning'" />
        </header>
        <a class="stream-link-button source-link" :href="source.channel_url" target="_blank" rel="noreferrer">
          <ExternalLink :size="16" />
          {{ $t("creator.open_channel") }}
        </a>
        <dl>
          <div>
            <dt>{{ $t("creator.owner") }}</dt>
            <dd>{{ source.user_id }}</dd>
          </div>
          <div>
            <dt>{{ $t("creator.external_short") }}</dt>
            <dd>{{ source.external_channel_id || $t("creator.auto") }}</dd>
          </div>
          <div>
            <dt>{{ $t("creator.ping") }}</dt>
            <dd>{{ roleName(source.ping_role_id) }}</dd>
          </div>
        </dl>
        <div class="source-actions">
          <button class="ghost-button compact" type="button" @click="editCreator(source)"><Pencil :size="15" /> {{ $t("common.edit") }}</button>
          <button class="ghost-button compact danger" type="button" @click="deleteCreator(source)"><Trash2 :size="15" /> {{ $t("common.delete") }}</button>
        </div>
      </article>
    </div>
  </section>
</template>
