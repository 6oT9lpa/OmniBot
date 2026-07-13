<script setup lang="ts">
import { computed, reactive } from "vue";
import { useActivityStore } from "../../stores/activity.store";
import { t } from "../../i18n";
import AuthenticatedImage from "../common/AuthenticatedImage.vue";

type DevBlogEditorEmbed = {
  title: string;
  description: string;
  image_url: string;
  color: number;
};

const activity = useActivityStore();
const saving = reactive({ value: false, message: "" });
const devBlogDraft = reactive({
  title: t("dev.default_title"),
  content: "",
  status: "published" as "draft" | "published",
  image_render_mode: "gallery_bottom" as "gallery_bottom" | "inline_between_text",
  embeds: [{ title: t("dev.release_note"), description: t("dev.first_body"), image_url: "", color: 0x5865f2 }],
});
const savedDrafts = computed(() => activity.devBlogPosts.filter((post) => post.status === "draft").slice(0, 10));

function colorToHex(value: number) {
  return `#${value.toString(16).padStart(6, "0").slice(-6)}`;
}

function addDevBlogEmbed() {
  if (devBlogDraft.embeds.length >= 10) return;
  devBlogDraft.embeds.push({ title: "", description: "", image_url: "", color: 0x5865f2 });
}

function removeDevBlogEmbed(index: number) {
  if (index === 0 || devBlogDraft.embeds.length <= 1) return;
  devBlogDraft.embeds.splice(index, 1);
}

async function saveDevBlog(status: "draft" | "published") {
  devBlogDraft.status = status;
  saving.value = true;
  saving.message = t(status === "draft" ? "dev.saving_draft" : "dev.publishing");
  try {
    await activity.createDevBlog({
      title: devBlogDraft.title,
      content: devBlogDraft.content || null,
      status,
      image_render_mode: devBlogDraft.image_render_mode,
      embeds: devBlogDraft.embeds.map((embed) => ({
        title: embed.title || null,
        description: embed.description,
        image_url: embed.image_url || null,
        color: embed.color,
      })),
    });
    saving.message = t(status === "draft" ? "dev.draft_saved" : "dev.published");
  } catch (error) {
    saving.message = error instanceof Error ? error.message : t("dev.channel_missing");
  } finally {
    saving.value = false;
  }
}

function channelName(id: unknown) {
  const value = String(id ?? "");
  return activity.textChannels.find((channel) => channel.id === value)?.name || value || "-";
}

function loadDraft(post: Record<string, unknown>) {
  const payload = parsePayload(post.payload_json);
  devBlogDraft.title = String(post.title || devBlogDraft.title);
  devBlogDraft.content = typeof payload.content === "string" ? payload.content : "";
  devBlogDraft.image_render_mode = payload.image_render_mode === "inline_between_text" ? "inline_between_text" : "gallery_bottom";
  devBlogDraft.status = "draft";
  devBlogDraft.embeds.splice(0, devBlogDraft.embeds.length, ...normalizeEmbeds(payload.embeds));
  saving.message = t("dev.draft_loaded");
}

function parsePayload(value: unknown) {
  if (typeof value !== "string") return {};
  try {
    return JSON.parse(value) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function normalizeEmbeds(value: unknown): DevBlogEditorEmbed[] {
  if (!Array.isArray(value) || value.length === 0) {
    return [{ title: t("dev.release_note"), description: "", image_url: "", color: 0x5865f2 }];
  }
  return value.slice(0, 10).map((embed) => {
    const source = embed as Record<string, unknown>;
    const image = source.image as Record<string, unknown> | undefined;
    return {
      title: typeof source.title === "string" ? source.title : "",
      description: typeof source.description === "string" ? source.description : "",
      image_url: typeof source.image_url === "string" ? source.image_url : typeof image?.url === "string" ? image.url : "",
      color: typeof source.color === "number" ? source.color : 0x5865f2,
    };
  });
}
</script>

<template>
  <section class="editor-grid preview-editor-grid">
    <form class="control-surface" @submit.prevent="saveDevBlog('published')">
      <div class="section-heading">
        <span>{{ $t("dev.eyebrow") }}</span>
        <h2>{{ $t("dev.heading") }}</h2>
        <div>
          <p>{{ $t("dev.description") }}</p>
        </div>
      </div>
      <label>
        {{ $t("welcome.title") }}
        <input v-model="devBlogDraft.title" maxlength="256" />
      </label>
      <label>
        {{ $t("dev.message_content") }}
        <textarea v-model="devBlogDraft.content" rows="3" maxlength="2000" />
      </label>
      <label class="toggle-row">
        <input
          type="checkbox"
          :checked="devBlogDraft.image_render_mode === 'inline_between_text'"
          @change="devBlogDraft.image_render_mode = ($event.target as HTMLInputElement).checked ? 'inline_between_text' : 'gallery_bottom'"
        />
        <span>{{ $t("dev.inline_images") }}</span>
      </label>
      <div class="embed-stack">
        <article v-for="(embed, index) in devBlogDraft.embeds" :key="index" class="embed-editor">
          <div class="discord-preview-header">
            <span>{{ $t("dev.embed_number", { number: index + 1 }) }}</span>
            <button
              v-if="index > 0"
              class="ghost-button compact"
              type="button"
              :disabled="devBlogDraft.embeds.length <= 1"
              @click="removeDevBlogEmbed(index)"
            >
              {{ $t("dev.remove") }}
            </button>
          </div>
          <label>
            {{ $t("dev.embed_title") }}
            <input v-model="embed.title" maxlength="256" />
          </label>
          <label>
            {{ $t("welcome.message") }}
            <textarea v-model="embed.description" rows="5" maxlength="4096" required />
          </label>
          <div class="form-grid">
            <label>
              {{ $t("dev.image_url") }}
              <input v-model="embed.image_url" maxlength="2048" placeholder="https://..." />
            </label>
            <label>
              {{ $t("welcome.color") }}
              <input
                type="color"
                :value="colorToHex(embed.color)"
                @input="embed.color = parseInt(($event.target as HTMLInputElement).value.replace('#', ''), 16)"
              />
            </label>
          </div>
        </article>
      </div>
      <div class="form-actions">
        <button class="primary-button" type="submit" :disabled="saving.value">{{ $t("dev.publish") }}</button>
        <button class="ghost-button" type="button" :disabled="saving.value || savedDrafts.length >= 10" @click="saveDevBlog('draft')">{{ $t("dev.save_draft") }}</button>
        <button class="ghost-button" type="button" :disabled="devBlogDraft.embeds.length >= 10" @click="addDevBlogEmbed">
          {{ $t("dev.add_embed") }}
        </button>
        <small>{{ saving.message }}</small>
      </div>
    </form>
    <article class="discord-preview sticky-preview">
      <div class="discord-preview-header"><span>{{ $t("dev.preview") }}</span><strong>{{ $t(`common.${devBlogDraft.status}`) }}</strong></div>
      <h3>{{ devBlogDraft.title }}</h3>
      <p>{{ devBlogDraft.content || devBlogDraft.embeds[0]?.description }}</p>
      <div
        v-for="(embed, index) in devBlogDraft.embeds"
        :key="`preview-${index}`"
        class="preview-media"
        :class="{ 'has-image': embed.image_url }"
      >
        <span>{{ embed.title || $t("dev.embed_number", { number: index + 1 }) }}</span>
        <AuthenticatedImage
          v-if="embed.image_url"
          :src="embed.image_url"
          :alt="$t('dev.preview_image_alt', { number: index + 1 })"
        />
        <small v-else>{{ $t("dev.no_image") }}</small>
      </div>
      <footer><span>{{ $t("dev.embed_count", { count: devBlogDraft.embeds.length }) }}</span><span>#{{ channelName(activity.channelPurposes.dev_blog) }}</span></footer>
      <small>{{ $t(devBlogDraft.image_render_mode === "inline_between_text" ? "dev.inline_help" : "dev.gallery_help") }}</small>
    </article>
  </section>
  <section class="panel-section">
    <div class="section-heading">
      <span>{{ $t("dev.history") }}</span>
      <h2>{{ $t("dev.saved_posts") }}</h2>
      <div>
        <p>{{ $t("dev.history_help") }}</p>
      </div>
    </div>
    <div v-if="savedDrafts.length" class="draft-button-row">
      <button
        v-for="post in savedDrafts"
        :key="`draft-${post.id}`"
        class="ghost-button compact"
        type="button"
        @click="loadDraft(post)"
      >
        {{ post.title }}
      </button>
    </div>
    <div class="record-list">
      <article v-for="post in activity.devBlogPosts" :key="String(post.id)">
        <strong>{{ post.title }}</strong>
        <span>{{ $t(`common.${post.status}`) }} - #{{ channelName(post.channel_id) }} - {{ post.created_at }}</span>
      </article>
    </div>
  </section>
</template>
