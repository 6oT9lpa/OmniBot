<script setup lang="ts">
import { computed, reactive } from "vue";
import { useActivityStore } from "../../stores/activity.store";

type DevBlogEditorEmbed = {
  title: string;
  description: string;
  image_url: string;
  color: number;
};

const activity = useActivityStore();
const saving = reactive({ value: false, message: "" });
const devBlogDraft = reactive({
  title: "OmniBot Activity update",
  content: "",
  status: "published" as "draft" | "published",
  embeds: [{ title: "Release note", description: "Write the first embed body.", image_url: "", color: 0x5865f2 }],
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
  saving.message = status === "draft" ? "Saving draft..." : "Publishing...";
  try {
    await activity.createDevBlog({
      title: devBlogDraft.title,
      content: devBlogDraft.content || null,
      status,
      embeds: devBlogDraft.embeds.map((embed) => ({
        title: embed.title || null,
        description: embed.description,
        image_url: embed.image_url || null,
        color: embed.color,
      })),
    });
    saving.message = status === "draft" ? "Draft saved" : "Published to Dev Blog";
  } catch (error) {
    saving.message = error instanceof Error ? error.message : "Dev Blog channel is not configured";
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
  devBlogDraft.status = "draft";
  devBlogDraft.embeds.splice(0, devBlogDraft.embeds.length, ...normalizeEmbeds(payload.embeds));
  saving.message = "Draft loaded";
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
    return [{ title: "Release note", description: "", image_url: "", color: 0x5865f2 }];
  }
  return value.slice(0, 10).map((embed) => {
    const source = embed as Record<string, unknown>;
    const image = source.image as Record<string, unknown> | undefined;
    return {
      title: typeof source.title === "string" ? source.title : "",
      description: typeof source.description === "string" ? source.description : "",
      image_url: typeof image?.url === "string" ? image.url : "",
      color: typeof source.color === "number" ? source.color : 0x5865f2,
    };
  });
}
</script>

<template>
  <section class="editor-grid">
    <form class="control-surface" @submit.prevent="saveDevBlog('published')">
      <div class="section-heading">
        <span>Developer publishing</span>
        <h2>Compose a multi-embed Dev Blog update.</h2>
      </div>
      <label>
        Title
        <input v-model="devBlogDraft.title" maxlength="256" />
      </label>
      <label>
        Message content
        <textarea v-model="devBlogDraft.content" rows="3" maxlength="2000" />
      </label>
      <div class="embed-stack">
        <article v-for="(embed, index) in devBlogDraft.embeds" :key="index" class="embed-editor">
          <div class="discord-preview-header">
            <span>Embed {{ index + 1 }}</span>
            <button
              v-if="index > 0"
              class="ghost-button compact"
              type="button"
              :disabled="devBlogDraft.embeds.length <= 1"
              @click="removeDevBlogEmbed(index)"
            >
              Remove
            </button>
          </div>
          <label>
            Embed title
            <input v-model="embed.title" maxlength="256" />
          </label>
          <label>
            Description
            <textarea v-model="embed.description" rows="5" maxlength="4096" required />
          </label>
          <div class="form-grid">
            <label>
              Image URL
              <input v-model="embed.image_url" maxlength="2048" placeholder="https://..." />
            </label>
            <label>
              Color
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
        <button class="primary-button" type="submit" :disabled="saving.value">Publish</button>
        <button class="ghost-button" type="button" :disabled="saving.value || savedDrafts.length >= 10" @click="saveDevBlog('draft')">Save Draft</button>
        <button class="ghost-button" type="button" :disabled="devBlogDraft.embeds.length >= 10" @click="addDevBlogEmbed">
          Add embed
        </button>
        <small>{{ saving.message }}</small>
      </div>
    </form>
    <article class="discord-preview">
      <div class="discord-preview-header"><span>Dev Blog preview</span><strong>{{ devBlogDraft.status }}</strong></div>
      <h3>{{ devBlogDraft.title }}</h3>
      <p>{{ devBlogDraft.content || devBlogDraft.embeds[0]?.description }}</p>
      <div v-for="(embed, index) in devBlogDraft.embeds" :key="`preview-${index}`" class="preview-media">
        <span>{{ embed.title || `Embed ${index + 1}` }}</span>
        <small>{{ embed.image_url || "No image" }}</small>
      </div>
      <footer><span>{{ devBlogDraft.embeds.length }}/10 embeds</span><span>#{{ channelName(activity.channelPurposes.dev_blog) }}</span></footer>
    </article>
  </section>
  <section class="panel-section">
    <div class="section-heading">
      <span>Publishing history</span>
      <h2>Saved Dev Blog posts.</h2>
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
        <span>{{ post.status }} - #{{ channelName(post.channel_id) }} - {{ post.created_at }}</span>
      </article>
    </div>
  </section>
</template>
