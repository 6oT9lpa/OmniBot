<script setup lang="ts">
import { ArrowUpRight, LockKeyhole } from "@lucide/vue";
import type { PanelModule } from "../../types/activity.types";

defineProps<{
  module: PanelModule;
  active?: boolean;
}>();
</script>

<template>
  <RouterLink
    :class="['module-card', module.status, { active }]"
    :to="module.permission === 'disabled' ? '/no-access' : `/panel/${module.key}`"
  >
    <span>{{ module.eyebrow }}</span>
    <h3>{{ module.title }}</h3>
    <p>{{ module.description }}</p>
    <div class="module-card-footer">
      <small>{{ module.permission === "disabled" ? $t("module.state.locked") : module.eyebrow }}</small>
      <LockKeyhole v-if="module.permission === 'disabled'" :size="17" />
      <ArrowUpRight v-else :size="17" />
    </div>
  </RouterLink>
</template>
