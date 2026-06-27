<script setup lang="ts">
import {
  Activity,
  BellRing,
  Bot,
  ChartNoAxesCombined,
  FileText,
  HeartPulse,
  LayoutDashboard,
  LockKeyhole,
  MessageSquareText,
  PanelsTopLeft,
  RadioTower,
  Settings,
  ShieldCheck,
  UsersRound,
  Volume2,
} from "@lucide/vue";
import type { ModuleKey, PanelModule } from "../../types/activity.types";

defineProps<{
  modules: PanelModule[];
  activeModule: ModuleKey;
}>();

const icons = {
  dashboard: LayoutDashboard,
  access: ShieldCheck,
  welcome: MessageSquareText,
  "role-panels": PanelsTopLeft,
  "creator-alerts": BellRing,
  "dev-blog": FileText,
  "ai-moderator": Bot,
  logs: Activity,
  "server-stats": ChartNoAxesCombined,
  "voice-rooms": Volume2,
  "bot-settings": Settings,
  integrations: RadioTower,
  health: HeartPulse,
};
</script>

<template>
  <aside class="panel-sidebar">
    <RouterLink class="panel-brand" to="/">
      <img class="panel-brand-logo" src="/omni-logo.png" alt="" />
      <strong>OMNI</strong>
      <span>activity</span>
    </RouterLink>

    <nav class="panel-nav" aria-label="Panel modules">
      <RouterLink
        v-for="module in modules"
        :key="module.key"
        :class="['panel-nav-item', { locked: module.permission === 'disabled', active: activeModule === module.key }]"
        :to="module.permission === 'disabled' ? '/no-access' : `/panel/${module.key}`"
      >
        <component :is="module.permission === 'disabled' ? LockKeyhole : icons[module.key]" :size="17" />
        <span>{{ module.title }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>
