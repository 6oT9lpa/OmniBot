<script setup lang="ts">
import { useActivityStore } from "../../stores/activity.store";
import type { ActivityRolePurpose } from "../../types/activity.types";
import AccessMatrixTable from "./AccessMatrixTable.vue";

const activity = useActivityStore();

const rolePurposes: Array<{ purpose: ActivityRolePurpose; label: string }> = [
  { purpose: "activity_admin", label: "Activity administrator" },
  { purpose: "activity_streamer", label: "Streamer" },
  { purpose: "activity_developer", label: "Developer" },
];
</script>

<template>
  <section class="panel-section">
    <div class="section-heading">
      <span>Permission matrix</span>
      <h2>Role-based access that scales with every module.</h2>
      <p>Bind Activity access levels to existing Discord roles.</p>
    </div>
    <div class="settings-list">
      <label v-for="item in rolePurposes" :key="item.purpose">
        {{ item.label }}
        <select
          :value="activity.activityRoles[item.purpose] || ''"
          @change="activity.saveActivityRolePurpose(item.purpose, ($event.target as HTMLSelectElement).value)"
        >
          <option value="" disabled>Select role</option>
          <option v-for="role in activity.roles" :key="role.id" :value="role.id">{{ role.name }}</option>
        </select>
      </label>
    </div>
    <AccessMatrixTable />
  </section>
</template>
