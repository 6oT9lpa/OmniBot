<script setup lang="ts">
import { ref } from "vue";
import { useActivityStore } from "../../stores/activity.store";
import StatCard from "./StatCard.vue";

const activity = useActivityStore();
const userSearch = ref("");

async function searchStatsUsers() {
  await activity.searchStatsUsers(userSearch.value);
}

function formatRecordValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function nestedValue(row: Record<string, unknown>, key: string, nestedKey: string) {
  const nested = row[key];
  if (!nested || typeof nested !== "object") return "-";
  return formatRecordValue((nested as Record<string, unknown>)[nestedKey]);
}
</script>

<template>
  <section class="panel-section">
    <div class="section-heading">
      <span>Server stats</span>
      <h2>Messages, channels and user activity.</h2>
    </div>
    <div class="stats-grid">
      <StatCard
        v-for="(value, key) in (activity.serverStats?.summary || {})"
        :key="String(key)"
        :metric="{ label: String(key), value: formatRecordValue(value), delta: 'last period', tone: 'neutral' }"
      />
    </div>
    <form class="module-toolbar" @submit.prevent="searchStatsUsers">
      <input v-model="userSearch" placeholder="Search Discord user" />
      <button class="primary-button" type="submit">Search</button>
    </form>
    <div class="record-list">
      <article v-for="row in activity.userStatsResults" :key="nestedValue(row, 'member', 'id')">
        <strong>{{ nestedValue(row, 'member', 'display_name') }}</strong>
        <span>{{ formatRecordValue(row.stats) }}</span>
      </article>
    </div>
    <div class="record-list compact-list">
      <article v-for="channel in (activity.serverStats?.channels || [])" :key="String(channel.channel_id)">
        <strong>#{{ channel.channel_name }}</strong>
        <span>{{ channel.messages }} messages</span>
      </article>
    </div>
  </section>
</template>
