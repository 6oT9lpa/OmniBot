<script setup lang="ts">
import { LockKeyhole } from "@lucide/vue";

defineProps<{
  title?: string;
  text?: string;
  actionLabel?: string;
  busy?: boolean;
}>();

defineEmits<{
  action: [];
}>();
</script>

<template>
  <section class="no-access-state">
    <div class="state-icon"><LockKeyhole :size="22" /></div>
    <h2>{{ title || "No module access" }}</h2>
    <p>{{ text || "An administrator can grant module permissions from Access Control." }}</p>
    <button v-if="actionLabel" class="primary-button" type="button" :disabled="busy" @click="$emit('action')">
      {{ busy ? "Syncing..." : actionLabel }}
    </button>
    <RouterLink class="secondary-link" to="/">Back to Omni</RouterLink>
  </section>
</template>
