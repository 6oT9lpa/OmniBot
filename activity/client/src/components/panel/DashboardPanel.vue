<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import { useActivityStore } from "../../stores/activity.store";
import { t, useI18n } from "../../i18n";
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
const { locale } = useI18n();
const latencyCooldown = ref(0);
let cooldownTimer: number | undefined;

const dashboardCards = computed<DashboardMetric[]>(() => {
  const metrics = activity.dashboard?.metrics;
  if (!metrics) {
    return [
      { key: "modules", label: t("dashboard.modules_ready"), value: "8/13", delta: t("dashboard.loaded_access"), tone: "success" },
      { key: "ai", label: t("dashboard.moderation_signals"), value: "0", delta: t("dashboard.review_items", { count: 0 }), tone: "neutral" },
      { key: "creators", label: t("dashboard.creator_sources"), value: "0", delta: t("dashboard.connected_sources"), tone: "neutral" },
      withLatencyState({ key: "latency", label: t("dashboard.bot_latency"), value: "-", delta: t("dashboard.click_refresh"), tone: "success" }),
    ] as DashboardMetric[];
  }

  return [
    {
      key: "modules",
      label: t("dashboard.modules_ready"),
      value: `${metrics.modules_ready}/${metrics.modules_total}`,
      delta: t("dashboard.loaded_access"),
      tone: "success",
    },
    {
      key: "ai",
      label: t("dashboard.moderation_signals"),
      value: String(metrics.ai_checks_today),
      delta: t("dashboard.review_items", { count: metrics.ai_flagged_today }),
      tone: metrics.ai_flagged_today > 0 ? "warning" : "neutral",
    },
    {
      key: "creators",
      label: t("dashboard.creator_sources"),
      value: String(metrics.creator_sources),
      delta: t("dashboard.connected_sources"),
      tone: metrics.creator_sources > 0 ? "success" : "neutral",
    },
    withLatencyState({
      key: "latency",
      label: t("dashboard.bot_latency"),
      value: activity.botLatencyMs === null ? t("dashboard.unavailable") : `${activity.botLatencyMs} ms`,
      delta: t("dashboard.click_refresh"),
      tone: activity.healthError ? "warning" : "success",
    }),
  ];
});

const auditEvents = computed<TimelineEvent[]>(() => {
  const rows = (activity.dashboard?.audit ?? activity.logs?.audit ?? []).slice(0, 5);
  if (!rows.length) return [];
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
    value: activity.botLatencyMs === null ? t("dashboard.unavailable") : `${activity.botLatencyMs} ms`,
    delta: latencyCooldown.value > 0 ? t("dashboard.refresh_in", { seconds: latencyCooldown.value }) : activity.healthError || metric.delta,
    tone: activity.healthError ? "warning" : metric.tone,
  };
}

function eventTitle(value: unknown) {
  const raw = String(value || "audit_event");
  const titles: Record<string, string> = {
    voice_join: t("dashboard.event.voice_join"),
    voice_leave: t("dashboard.event.voice_leave"),
    voice_move: t("dashboard.event.voice_move"),
    activity_synced_role_assignments_updated: t("dashboard.event.roles_updated"),
    activity_welcome_test_sent: t("dashboard.event.welcome_test"),
  };
  return titles[raw] || raw.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function eventDetail(row: Record<string, unknown>) {
  const type = String(row.event_type || "");
  const details = parseDetails(row.details);
  if (type === "voice_join" && details.channel) return t("dashboard.event.joined", { channel: String(details.channel) });
  if (type === "voice_leave" && details.channel) return t("dashboard.event.left", { channel: String(details.channel) });
  if (type === "voice_move") {
    return t("dashboard.event.moved", { before: String(details.before_channel || t("dashboard.unknown")), after: String(details.after_channel || t("dashboard.unknown")) });
  }
  if (typeof row.details === "string" && row.details.trim()) return row.details;
  return String(row.target_name || t("dashboard.no_details"));
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
  if (!raw) return t("dashboard.recent");
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleString(locale.value === "ru" ? "ru-RU" : "en-US");
}

onBeforeUnmount(() => {
  if (cooldownTimer) window.clearInterval(cooldownTimer);
});
</script>

<template>
  <RevealOnScroll tag="section" class="dashboard-hero">
    <div>
      <span class="eyebrow">{{ $t("dashboard.eyebrow") }}</span>
      <h2>{{ $t("dashboard.heading") }}</h2>
      <p>{{ $t("dashboard.description") }}</p>
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

  <ActivityTimeline :events="auditEvents" :action-label="$t('dashboard.details')" action-to="/panel/logs" />
</template>
