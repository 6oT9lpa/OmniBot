<script setup lang="ts">
import type { WelcomeConfig } from "../../types/activity.types";

const props = defineProps<{
  config: WelcomeConfig;
}>();

function hexColor(color: number) {
  return `#${color.toString(16).padStart(6, "0").slice(-6)}`;
}

function previewText(value: string) {
  return value
    .replaceAll("{user}", "@User")
    .replaceAll("{username}", "User")
    .replaceAll("{server}", "Omni Server")
    .replaceAll("{guild}", "Omni Server")
    .replaceAll("{member_count}", "1,248")
    .replaceAll("{joined_at}", "today")
    .replaceAll("{rules}", "#rules")
    .replaceAll("{roles}", "#roles");
}
</script>

<template>
  <article class="discord-preview" :style="{ borderColor: hexColor(props.config.color) }">
    <div class="discord-preview-header">
      <span>Discord preview</span>
      <strong>{{ config.is_enabled ? "Enabled" : "Disabled" }}</strong>
    </div>
    <h3>{{ config.title }}</h3>
    <p>{{ previewText(config.description) }}</p>
    <div class="preview-media">
      {{ config.thumbnail_url || "Thumbnail area" }}
    </div>
    <footer>
      <span>{{ config.footer_text || "OmniBot Activity" }}</span>
      <span>{{ hexColor(config.color) }}</span>
    </footer>
  </article>
</template>
