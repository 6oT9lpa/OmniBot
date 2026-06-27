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
      <div>
        <span>Audit stream</span>
        <h2>Recent Activity</h2>
      </div>
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
