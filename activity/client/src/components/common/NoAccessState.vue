<script setup lang="ts">
import { LockKeyhole } from "@lucide/vue";

defineProps<{
  title?: string;
  text?: string;
}>();
</script>

<template>
  <section class="no-access-state">
    <div class="state-icon"><LockKeyhole :size="22" /></div>
    <h2>{{ title || "No module access" }}</h2>
    <p>{{ text || "An administrator can grant module permissions from Access Control." }}</p>
    <RouterLink class="secondary-link" to="/">Back to Omni</RouterLink>
  </section>
</template>
