<script setup lang="ts">
import type { DashboardMetric } from "../../types/activity.types";

defineProps<{
  metric: DashboardMetric;
}>();
</script>

<template>
  <article :class="['stat-card', metric.tone]">
    <span>{{ metric.label }}</span>
    <strong>{{ metric.value }}</strong>
    <small>{{ metric.delta }}</small>
  </article>
</template>
