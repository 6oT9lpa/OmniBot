<script setup lang="ts">
import { Moon, Sun } from "@lucide/vue";
import { useActivityStore } from "../../stores/activity.store";
import StatusBadge from "../common/StatusBadge.vue";

defineProps<{
  title: string;
  subtitle: string;
}>();

const activity = useActivityStore();
</script>

<template>
  <header class="panel-topbar">
    <div>
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>
    </div>
    <div class="panel-user">
      <StatusBadge :label="activity.session?.access_level || 'preview'" tone="success" />
      <button class="icon-button" type="button" title="Toggle theme" @click="activity.toggleTheme()">
        <Sun v-if="activity.theme === 'dark'" :size="18" />
        <Moon v-else :size="18" />
      </button>
    </div>
  </header>
</template>
