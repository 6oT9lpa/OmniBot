<script setup lang="ts">
import { ref } from "vue";
import { useActivityStore } from "../../stores/activity.store";

const activity = useActivityStore();
const logQuery = ref("");
const logSource = ref<"all" | "messages" | "audit">("all");
const logEventType = ref("");

async function loadLogs() {
  await activity.loadLogs(logSource.value, logEventType.value, logQuery.value);
}
</script>

<template>
  <section class="panel-section">
    <div class="section-heading">
      <span>Logs</span>
      <h2>Searchable message and audit logs.</h2>
    </div>
    <form class="module-toolbar" @submit.prevent="loadLogs">
      <select v-model="logSource">
        <option value="all">All</option>
        <option value="messages">Messages</option>
        <option value="audit">Audit</option>
      </select>
      <input v-model="logEventType" placeholder="Event type" />
      <input v-model="logQuery" placeholder="Search logs" />
      <button class="primary-button" type="submit">Apply</button>
    </form>
    <div class="record-list">
      <article v-for="row in (activity.logs?.audit || [])" :key="`audit-${row.id}`">
        <strong>{{ row.event_type }}</strong>
        <span>{{ row.actor_name || row.target_name }} · {{ row.details }} · {{ row.created_at }}</span>
      </article>
      <article v-for="row in (activity.logs?.messages || [])" :key="`message-${row.id}`">
        <strong>{{ row.event_type }}</strong>
        <span>{{ row.author_name }} · {{ row.content }} · {{ row.created_at }}</span>
      </article>
    </div>
  </section>
</template>
