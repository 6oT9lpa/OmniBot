<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useActivityStore } from "../../stores/activity.store";
import StatCard from "./StatCard.vue";

type StatsTab = "summary" | "chart" | "users" | "channels";

const activity = useActivityStore();
const activeTab = ref<StatsTab>("summary");
const userSearch = ref("");
let searchTimer: number | undefined;
const tabs: Array<{ key: StatsTab; label: string }> = [
  { key: "summary", label: "Total stats" },
  { key: "chart", label: "30 day chart" },
  { key: "users", label: "User stats" },
  { key: "channels", label: "Channel stats" },
];
const dailyStats = computed(() => activity.serverStats?.daily?.slice(-30) || []);
const maxDaily = computed(() => Math.max(1, ...dailyStats.value.map((row) => row.count)));
const summaryCards = computed(() => {
  const summary = activity.serverStats?.summary || {};
  return [
    ["total_messages", "Total messages"],
    ["active_users", "Active users"],
    ["active_channels", "Active channels"],
    ["voice_total_voice_minutes", "Voice minutes"],
    ["voice_voice_users", "Voice users"],
    ["joins", "Joins"],
    ["leaves", "Leaves"],
    ["period_days", "Period days"],
  ].map(([key, label]) => ({ key, label, value: formatRecordValue(summary[key]), delta: key === "period_days" ? "selected range" : "tracked activity", tone: "neutral" as const }));
});

async function searchStatsUsers() { await activity.searchStatsUsers(userSearch.value); }
function selectUser(row: Record<string, unknown>) { const member = row.member as Record<string, unknown> | undefined; userSearch.value = String(member?.display_name || member?.username || ""); }
function formatRecordValue(value: unknown) { if (value === null || value === undefined || value === "") return "-"; return typeof value === "object" ? JSON.stringify(value) : String(value); }
function nestedValue(row: Record<string, unknown>, key: string, nestedKey: string) { const nested = row[key]; return !nested || typeof nested !== "object" ? "-" : formatRecordValue((nested as Record<string, unknown>)[nestedKey]); }
function statValue(row: Record<string, unknown>, key: string) { const stats = row.stats; return !stats || typeof stats !== "object" ? "-" : formatRecordValue((stats as Record<string, unknown>)[key]); }

watch(userSearch, (value) => {
  if (searchTimer) window.clearTimeout(searchTimer);
  if (value.trim().length < 2) { activity.userStatsResults = []; return; }
  searchTimer = window.setTimeout(() => { void searchStatsUsers(); }, 250);
});
</script>

<template>
  <section class="panel-section ai-moderation-hero">
    <div class="section-heading">
      <span>Server stats</span>
      <h2>Messages, channels and user activity.</h2>
      <div><p>Review message volume, active members, voice time and channel trends for the selected period.</p></div>
    </div>
    <nav class="ai-moderation-nav" aria-label="Server statistics">
      <button v-for="tab in tabs" :key="tab.key" type="button" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</button>
    </nav>
  </section>

  <section v-if="activeTab === 'summary'" class="panel-section stats-summary-panel">
    <div class="stats-grid"><StatCard v-for="metric in summaryCards" :key="metric.key" :metric="metric" /></div>
  </section>

  <section v-else-if="activeTab === 'chart'" class="panel-section stats-chart-panel">
    <div class="section-heading"><span>30 day chart</span><h2>Message activity by day.</h2></div>
    <div class="stats-daily"><div v-for="point in dailyStats" :key="point.date" class="stats-day"><span :style="{ height: `${Math.max(4, (point.count / maxDaily) * 100)}%` }"></span><small>{{ point.date.slice(5) }}</small></div></div>
  </section>

  <section v-else-if="activeTab === 'users'" class="panel-section stats-search-panel">
    <form class="module-toolbar" @submit.prevent="searchStatsUsers"><input v-model="userSearch" placeholder="Search Discord user" /><button class="primary-button" type="submit">Search</button></form>
    <div v-if="activity.userStatsResults.length" class="user-suggestion-list"><button v-for="row in activity.userStatsResults" :key="nestedValue(row, 'member', 'id')" type="button" @click="selectUser(row)">{{ nestedValue(row, "member", "display_name") }}</button></div>
    <div class="record-list user-stat-list"><article v-for="row in activity.userStatsResults" :key="nestedValue(row, 'member', 'id')"><strong>{{ nestedValue(row, "member", "display_name") }}</strong><span>Messages: {{ statValue(row, "messages_count") }}</span><span>Voice minutes: {{ statValue(row, "voice_minutes") }}</span><span>Warnings: {{ statValue(row, "warnings_count") }}</span><span>Last message: {{ statValue(row, "last_message") }}</span></article></div>
  </section>

  <section v-else class="panel-section stats-channel-panel">
    <div class="section-heading"><span>Channels</span><h2>Top message channels.</h2></div>
    <div class="record-list compact-list channel-stat-list"><article v-for="channel in (activity.serverStats?.channels || [])" :key="String(channel.channel_id)"><strong>#{{ channel.channel_name }}</strong><span>{{ formatRecordValue(channel.messages) }} messages</span></article></div>
  </section>
</template>
