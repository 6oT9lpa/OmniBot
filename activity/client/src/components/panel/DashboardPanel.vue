<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import { useActivityStore } from "../../stores/activity.store";
import { dashboardMetrics, timelineEvents } from "../../stores/mock-data";
import type { DashboardMetric, PanelModule, TimelineEvent } from "../../types/activity.types";
import ActivityTimeline from "./ActivityTimeline.vue";
import ModuleCard from "./ModuleCard.vue";
import StatCard from "./StatCard.vue";

defineProps<{
  modules: PanelModule[];
  activeModule: string;
}>();

const activity = useActivityStore();
const latencyCooldown = ref(0);
let cooldownTimer: number | undefined;

const dashboardCards = computed<DashboardMetric[]>(() => {
  const metrics = activity.dashboard?.metrics;
  if (!metrics) {
    return dashboardMetrics.map((metric) =>
      metric.label === "Bot latency" ? withLatencyState({ ...metric, key: "latency" }) : metric,
    );
  }

  return [
    {
      key: "modules",
      label: "Modules ready",
      value: `${metrics.modules_ready}/${metrics.modules_total}`,
      delta: "Loaded from access map",
      tone: "success",
    },
    {
      key: "ai",
      label: "AI checks today",
      value: String(metrics.ai_checks_today),
      delta: `${metrics.ai_flagged_today} flagged`,
      tone: metrics.ai_flagged_today > 0 ? "warning" : "neutral",
    },
    {
      key: "creators",
      label: "Creator sources",
      value: String(metrics.creator_sources),
      delta: "Connected sources",
      tone: metrics.creator_sources > 0 ? "success" : "neutral",
    },
    withLatencyState({
      key: "latency",
      label: "Bot latency",
      value: activity.botLatencyMs === null ? "Unavailable" : `${activity.botLatencyMs} ms`,
      delta: "Click to refresh",
      tone: activity.healthError ? "warning" : "success",
    }),
  ];
});

const auditEvents = computed<TimelineEvent[]>(() => {
  const rows = (activity.dashboard?.audit ?? activity.logs?.audit ?? []).slice(0, 5);
  if (!rows.length) return timelineEvents;
  return rows.map((row, index) => ({
    id: String(row.id ?? index),
    title: String(row.event_type ?? "audit_event"),
    detail: String(row.details ?? row.target_name ?? "No details"),
    time: String(row.created_at ?? "recent"),
    tone: "neutral" as const,
  }));
});

async function refreshLatency(metric: DashboardMetric) {
  if (metric.key !== "latency" || latencyCooldown.value > 0) return;
  await activity.refreshHealth(true);
  latencyCooldown.value = 15;
  cooldownTimer = window.setInterval(() => {
    latencyCooldown.value -= 1;
    if (latencyCooldown.value <= 0 && cooldownTimer) {
      window.clearInterval(cooldownTimer);
      cooldownTimer = undefined;
    }
  }, 1000);
}

function withLatencyState(metric: DashboardMetric): DashboardMetric {
  return {
    ...metric,
    value: activity.botLatencyMs === null ? "Unavailable" : `${activity.botLatencyMs} ms`,
    delta: latencyCooldown.value > 0 ? `Refresh in ${latencyCooldown.value}s` : activity.healthError || metric.delta,
    tone: activity.healthError ? "warning" : metric.tone,
  };
}

onBeforeUnmount(() => {
  if (cooldownTimer) window.clearInterval(cooldownTimer);
});
</script>

<template>
  <section class="dashboard-hero">
    <div>
      <span class="eyebrow">Overview</span>
      <h2>Server operations at a glance.</h2>
      <p>A compact workspace for permissions, publishing, creator tools, AI signals and system health.</p>
    </div>
  </section>

  <section class="stats-grid">
    <button
      v-for="metric in dashboardCards"
      :key="metric.label"
      class="stat-button"
      type="button"
      :disabled="metric.key !== 'latency' || latencyCooldown > 0"
      @click="refreshLatency(metric)"
    >
      <StatCard :metric="metric" />
    </button>
  </section>

  <section class="module-grid">
    <ModuleCard
      v-for="module in modules"
      :key="module.key"
      :module="module"
      :active="activeModule === module.key"
    />
  </section>

  <ActivityTimeline :events="auditEvents" action-label="Details" action-to="/panel/logs" />
</template>
