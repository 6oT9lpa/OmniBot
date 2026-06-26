<script setup lang="ts">
import { computed } from "vue";
import StatusBadge from "../common/StatusBadge.vue";
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

const dashboardCards = computed<DashboardMetric[]>(() =>
  dashboardMetrics.map((metric) =>
    metric.label === "Bot latency"
      ? {
          ...metric,
          value: activity.botLatencyMs === null ? "Unavailable" : `${activity.botLatencyMs} ms`,
          delta: activity.healthLoading ? "Refreshing..." : activity.healthError || "Click health to refresh",
          tone: activity.healthError ? "warning" : metric.tone,
        }
      : metric,
  ),
);

const auditEvents = computed<TimelineEvent[]>(() => {
  const rows = (activity.logs?.audit ?? []).slice(0, 8);
  if (!rows.length) return timelineEvents;
  return rows.map((row, index) => ({
    id: String(row.id ?? index),
    title: String(row.event_type ?? "audit_event"),
    detail: String(row.details ?? row.target_name ?? "No details"),
    time: String(row.created_at ?? "recent"),
    tone: "neutral" as const,
  }));
});
</script>

<template>
  <section class="dashboard-hero">
    <div>
      <span class="eyebrow">Overview</span>
      <h2>Server operations at a glance.</h2>
      <p>A compact workspace for permissions, publishing, creator tools, AI signals and system health.</p>
    </div>
    <StatusBadge :label="activity.mode === 'local' ? 'local preview' : 'discord live'" tone="success" />
  </section>

  <section class="stats-grid">
    <StatCard v-for="metric in dashboardCards" :key="metric.label" :metric="metric" />
  </section>

  <section class="module-grid">
    <ModuleCard
      v-for="module in modules"
      :key="module.key"
      :module="module"
      :active="activeModule === module.key"
    />
  </section>

  <ActivityTimeline :events="auditEvents" />
</template>
