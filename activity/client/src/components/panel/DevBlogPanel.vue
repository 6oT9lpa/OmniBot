<script setup lang="ts">
import { reactive } from "vue";
import { useActivityStore } from "../../stores/activity.store";

const activity = useActivityStore();
const saving = reactive({ value: false, message: "" });
const devBlogDraft = reactive({
  title: "OmniBot Activity update",
  content: "",
  status: "published" as "draft" | "published",
  embeds: [{ title: "Release note", description: "Write the first embed body.", image_url: "", color: 0x5865f2 }],
});

function colorToHex(value: number) {
  return `#${value.toString(16).padStart(6, "0").slice(-6)}`;
}

function addDevBlogEmbed() {
  if (devBlogDraft.embeds.length >= 10) return;
  devBlogDraft.embeds.push({ title: "", description: "", image_url: "", color: 0x5865f2 });
}

function removeDevBlogEmbed(index: number) {
  if (devBlogDraft.embeds.length <= 1) return;
  devBlogDraft.embeds.splice(index, 1);
}

async function saveDevBlog(status: "draft" | "published") {
  devBlogDraft.status = status;
  saving.value = true;
  saving.message = status === "draft" ? "Saving draft..." : "Publishing...";
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
  saving.value = false;
  saving.message = status === "draft" ? "Draft saved" : "Published to Dev Blog";
}

function channelName(id: unknown) {
  const value = String(id ?? "");
  return activity.textChannels.find((channel) => channel.id === value)?.name || value || "-";
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
            <button class="ghost-button compact" type="button" :disabled="devBlogDraft.embeds.length <= 1" @click="removeDevBlogEmbed(index)">Remove</button>
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
        <button class="primary-button" type="submit">Publish</button>
        <button class="ghost-button" type="button" @click="saveDevBlog('draft')">Save Draft</button>
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
    <div class="record-list">
      <article v-for="post in activity.devBlogPosts" :key="String(post.id)">
        <strong>{{ post.title }}</strong>
        <span>{{ post.status }} · #{{ channelName(post.channel_id) }} · {{ post.created_at }}</span>
      </article>
    </div>
  </section>
</template>
