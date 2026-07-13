<script setup lang="ts">
import { Moon, Sun } from "@lucide/vue";
import { useActivityStore } from "../../stores/activity.store";
import LanguageSwitcher from "../common/LanguageSwitcher.vue";
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
      <StatusBadge :label="activity.session ? $t(`permission.${activity.session.access_level}`) : $t('panel.preview')" tone="success" />
      <LanguageSwitcher />
      <button class="icon-button" type="button" :title="$t('common.theme.toggle')" :aria-label="$t('common.theme.toggle')" @click="activity.toggleTheme()">
        <Sun v-if="activity.theme === 'dark'" :size="18" />
        <Moon v-else :size="18" />
      </button>
    </div>
  </header>
</template>
