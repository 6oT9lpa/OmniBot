<script setup lang="ts">
import { useActivityStore } from "../../stores/activity.store";

const activity = useActivityStore();

function formatRecordValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
</script>

<template>
  <section class="panel-section">
    <div class="section-heading">
      <span>Bot settings</span>
      <h2>Runtime configuration exposed safely.</h2>
    </div>
    <div class="settings-list">
      <article v-for="(value, key) in (activity.botSettings || {})" :key="String(key)">
        <strong>{{ key }}</strong>
        <span>{{ formatRecordValue(value) }}</span>
      </article>
    </div>
  </section>
</template>
