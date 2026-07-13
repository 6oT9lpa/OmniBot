<script setup lang="ts">
import type { TimelineEvent } from "../../types/activity.types";

defineProps<{
  events: TimelineEvent[];
  actionLabel?: string;
  actionTo?: string;
}>();
</script>

<template>
  <section class="panel-section">
    <div class="section-heading">
      <span>{{ $t("dashboard.audit_stream") }}</span>
      <h2>{{ $t("dashboard.recent_activity") }}</h2>
      <RouterLink v-if="actionLabel && actionTo" class="ghost-button" :to="actionTo">{{ actionLabel }}</RouterLink>
    </div>
    <div class="timeline">
      <article v-for="event in events" :key="event.id" :class="['timeline-item', event.tone]">
        <small>{{ event.time }}</small>
        <h3>{{ event.title }}</h3>
        <p>{{ event.detail }}</p>
      </article>
    </div>
  </section>
</template>
