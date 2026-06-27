<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useActivityStore } from "../../stores/activity.store";

const activity = useActivityStore();
const logQuery = ref("");
const actorQuery = ref("");
const dateFrom = ref("");
const dateTo = ref("");
const page = ref(0);
const pageSize = 20;

const totalPages = computed(() => Math.max(1, Math.ceil((activity.auditPage?.total ?? 0) / pageSize)));

async function loadAudit() {
  await activity.loadAuditPage({
    q: logQuery.value,
    actor: actorQuery.value,
    date_from: dateFrom.value,
    date_to: dateTo.value,
    limit: pageSize,
    offset: page.value * pageSize,
  });
}

async function applyFilters() {
  page.value = 0;
  await loadAudit();
}

async function goPage(delta: number) {
  page.value = Math.min(Math.max(page.value + delta, 0), totalPages.value - 1);
  await loadAudit();
}

onMounted(() => {
  void loadAudit();
});
</script>

<template>
  <section class="panel-section">
    <div class="section-heading">
      <span>Logs</span>
      <h2>Searchable audit stream.</h2>
      <p>Filter panel actions by event, date and the user who performed the action.</p>
    </div>
    <form class="module-toolbar" @submit.prevent="applyFilters">
      <input v-model="logQuery" placeholder="Search event or details" />
      <input v-model="actorQuery" placeholder="User or actor id" />
      <input v-model="dateFrom" type="datetime-local" />
      <input v-model="dateTo" type="datetime-local" />
      <button class="primary-button" type="submit">Apply</button>
    </form>
    <div class="record-list">
      <article v-for="row in activity.auditPage?.items || []" :key="`audit-${row.id}`">
        <strong>{{ row.event_type }}</strong>
        <span>{{ row.actor_name || row.actor_id || "system" }} · {{ row.details }} · {{ row.created_at }}</span>
      </article>
    </div>
    <div class="pagination-row">
      <button class="ghost-button compact" type="button" :disabled="page === 0" @click="goPage(-1)">Previous</button>
      <span>{{ page + 1 }} / {{ totalPages }}</span>
      <button class="ghost-button compact" type="button" :disabled="page + 1 >= totalPages" @click="goPage(1)">Next</button>
    </div>
  </section>
</template>
