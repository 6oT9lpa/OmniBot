<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";
import { useActivityStore } from "../../stores/activity.store";

const props = defineProps<{
  src: string;
  alt: string;
}>();

const activity = useActivityStore();
const resolvedSrc = ref("");
const failed = ref(false);
let objectUrl: string | null = null;
let requestController: AbortController | null = null;

function releaseObjectUrl() {
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = null;
}

async function loadImage() {
  requestController?.abort();
  requestController = new AbortController();
  releaseObjectUrl();
  resolvedSrc.value = "";
  failed.value = false;

  if (!activity.token || !activity.session) {
    resolvedSrc.value = props.src;
    return;
  }

  try {
    const query = new URLSearchParams({
      guild_id: activity.session.guild_id,
      url: props.src,
    });
    const response = await fetch(`/api/media/image?${query.toString()}`, {
      headers: { Authorization: `Bearer ${activity.token}` },
      signal: requestController.signal,
    });
    if (!response.ok) throw new Error(`Image proxy returned ${response.status}`);

    objectUrl = URL.createObjectURL(await response.blob());
    resolvedSrc.value = objectUrl;
    console.info("[preview-image] Image loaded through Activity media proxy");
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    failed.value = true;
    console.warn("[preview-image] Unable to load preview image", error);
  }
}

watch(
  () => [props.src, activity.token, activity.session?.guild_id],
  loadImage,
  { immediate: true },
);

onBeforeUnmount(() => {
  requestController?.abort();
  releaseObjectUrl();
});
</script>

<template>
  <img v-if="resolvedSrc && !failed" :src="resolvedSrc" :alt="props.alt" @error="failed = true" />
  <span v-else-if="failed" class="preview-image-error">{{ $t("common.image_unavailable") }}</span>
</template>
