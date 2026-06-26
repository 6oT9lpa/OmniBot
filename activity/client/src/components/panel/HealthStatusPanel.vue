<script setup lang="ts">
import { useActivityStore } from "../../stores/activity.store";

const activity = useActivityStore();

async function refreshHealth() {
  await activity.refreshHealth();
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
      <span>{{ signal.name }}</span>
      <strong>{{ signal.value }}</strong>
      <small>{{ activity.healthLoading ? "refreshing" : signal.status }}</small>
    </article>
  </section>
</template>
