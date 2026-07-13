<script setup lang="ts">
import { useActivityStore } from "../../stores/activity.store";
import { t } from "../../i18n";

const activity = useActivityStore();

async function refreshHealth() {
  await activity.refreshHealth();
}

function signalName(name: string) {
  const keys: Record<string, string> = {
    "Bot latency": "health.bot_latency",
    PostgreSQL: "health.postgresql",
    "AI Moderator": "health.ai_moderator",
    "Stream platform polling": "health.stream_polling",
  };
  return keys[name] ? t(keys[name]) : name;
}

function signalValue(name: string, value: string, latency?: number | null) {
  if (value === "Unavailable") return t("dashboard.unavailable");
  if (name === "Stream platform polling" && latency !== null && latency !== undefined) {
    return t("health.every_seconds", { seconds: latency });
  }
  return value;
}
</script>

<template>
  <section class="health-grid">
    <article
      v-for="signal in activity.healthSignals"
      :key="signal.name"
      :class="['health-card', signal.status, { refreshing: activity.healthLoading }]"
      role="button"
      tabindex="0"
      @click="refreshHealth"
      @keydown.enter.prevent="refreshHealth"
      @keydown.space.prevent="refreshHealth"
    >
      <span>{{ signalName(signal.name) }}</span>
      <strong>{{ signalValue(signal.name, signal.value, signal.latency_ms) }}</strong>
      <small>{{ activity.healthLoading ? $t("health.refreshing") : $t(`health.${signal.status}`) }}</small>
    </article>
  </section>
</template>
