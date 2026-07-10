<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import { useActivityStore } from "../../stores/activity.store";
import { dashboardMetrics, timelineEvents } from "../../stores/mock-data";
import type { DashboardMetric, PanelModule, TimelineEvent } from "../../types/activity.types";
import ActivityTimeline from "./ActivityTimeline.vue";
import ModuleCard from "./ModuleCard.vue";
import StatCard from "./StatCard.vue";
import RevealOnScroll from "../common/RevealOnScroll.vue";

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
      label: "Moderation signals",
      value: String(metrics.ai_checks_today),
      delta: `${metrics.ai_flagged_today} review items`,
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
    title: eventTitle(row.event_type),
    detail: eventDetail(row),
    time: formatTime(row.created_at),
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

function eventTitle(value: unknown) {
  const raw = String(value || "audit_event");
  const titles: Record<string, string> = {
    voice_join: "Voice join",
    voice_leave: "Voice leave",
    voice_move: "Voice move",
    activity_synced_role_assignments_updated: "Activity role assignments updated",
    activity_welcome_test_sent: "Welcome test sent",
  };
  return titles[raw] || raw.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function eventDetail(row: Record<string, unknown>) {
  const type = String(row.event_type || "");
  const details = parseDetails(row.details);
  if (type === "voice_join" && details.channel) return `Joined voice channel ${details.channel}.`;
  if (type === "voice_leave" && details.channel) return `Left voice channel ${details.channel}.`;
  if (type === "voice_move") {
    return `Moved from ${details.before_channel || "unknown"} to ${details.after_channel || "unknown"}.`;
  }
  if (typeof row.details === "string" && row.details.trim()) return row.details;
  return String(row.target_name || "No details recorded.");
}

function parseDetails(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object") return value as Record<string, unknown>;
  const raw = String(value || "");
  if (!raw.trim()) return {};
  try {
    return JSON.parse(raw.replaceAll("'", "\""));
  } catch {
    return {};
  }
}

function formatTime(value: unknown) {
  const raw = String(value || "");
  if (!raw) return "recent";
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleString();
}

onBeforeUnmount(() => {
  if (cooldownTimer) window.clearInterval(cooldownTimer);
});
</script>

<template>
  <RevealOnScroll tag="section" class="dashboard-hero">
    <div>
      <span class="eyebrow">OmniBot control center</span>
      <h2>Live server operations in one Activity.</h2>
      <p>Manage permissions, Creator Alerts, Dev Blog posts, AI moderation signals, voice rooms, logs and service health from the same protected workspace.</p>
    </div>
  </RevealOnScroll>

  <section class="stats-grid">
    <RevealOnScroll
      v-for="metric in dashboardCards"
      :key="metric.label"
      :delay="dashboardCards.indexOf(metric) * 45"
    >
    <button
      class="stat-button"
      type="button"
      :disabled="metric.key !== 'latency' || latencyCooldown > 0"
      @click="refreshLatency(metric)"
    >
      <StatCard :metric="metric" />
    </button>
    </RevealOnScroll>
  </section>

  <section class="module-grid">
    <RevealOnScroll
      v-for="module in modules"
      :key="module.key"
      :delay="modules.indexOf(module) * 35"
    >
    <ModuleCard
      :module="module"
      :active="activeModule === module.key"
    />
    </RevealOnScroll>
  </section>

  <ActivityTimeline :events="auditEvents" action-label="Details" action-to="/panel/logs" />
</template>
