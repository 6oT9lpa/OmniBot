<script setup lang="ts">
import { computed } from "vue";
import { useActivityStore } from "../../stores/activity.store";
import { t } from "../../i18n";

const activity = useActivityStore();
const integrationRows = computed(() =>
  Object.entries(activity.integrations || {}).map(([key, value]) => ({
    key,
    title: t(`integrations.${key}`),
    status: integrationStatus(value),
    details: integrationDetails(value),
  })),
);

function integrationStatus(value: unknown) {
  if (Array.isArray(value)) return value.length ? t("integrations.sources", { count: value.length }) : t("integrations.no_sources");
  if (value && typeof value === "object") {
    return t(`integrations.${String((value as Record<string, unknown>).status || "configured")}`);
  }
  return formatRecordValue(value);
}

function integrationDetails(value: unknown) {
  if (Array.isArray(value)) {
    if (!value.length) return t("integrations.no_platforms");
    return value
      .map((row) => {
        const item = row as Record<string, unknown>;
        return t("integrations.active_sources", { platform: String(item.platform), active: Number(item.active_count || 0), total: Number(item.count || 0) });
      })
      .join(", ");
  }
  if (value && typeof value === "object") {
    const item = value as Record<string, unknown>;
    if (Array.isArray(item.sources)) {
      const sourceDetails = item.sources
        .map((source) => {
          const row = source as Record<string, unknown>;
          return t("integrations.active_sources", { platform: String(row.platform), active: Number(row.active_count || 0), total: Number(row.count || 0) });
        })
        .join(", ");
      const interval = item.poll_interval_seconds ? t("integrations.poll_interval", { seconds: Number(item.poll_interval_seconds) }) : "";
      return [interval, sourceDetails || t("integrations.no_creator_sources")].filter(Boolean).join(" ");
    }
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${key}: ${formatRecordValue(item)}`)
      .join(", ");
  }
  return formatRecordValue(value);
}

function formatRecordValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
</script>

<template>
  <section class="panel-section">
    <div class="section-heading">
      <span>{{ $t("module.integrations") }}</span>
      <h2>{{ $t("integrations.heading") }}</h2>
      <div>
        <p>{{ $t("integrations.description") }}</p>
      </div>
    </div>
    <div class="integration-grid">
      <article v-for="row in integrationRows" :key="row.key" class="integration-card">
        <span class="status-badge success">{{ row.status }}</span>
        <strong>{{ row.title }}</strong>
        <p>{{ row.details }}</p>
      </article>
    </div>
  </section>
</template>
