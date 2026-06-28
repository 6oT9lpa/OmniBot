<script setup lang="ts">
import { computed } from "vue";
import { RefreshCcw } from "@lucide/vue";
import { useActivityStore } from "../../stores/activity.store";

const activity = useActivityStore();
const availableRoles = computed(() => activity.accessRoles);

function hasAssignment(discordRoleId: string, accessRoleId: number) {
  const syncedRole = activity.syncedRoles.find((role) => role.role_id === discordRoleId);
  return Boolean(syncedRole?.access_roles.some((role) => role.id === accessRoleId));
}

async function toggleAssignment(discordRoleId: string, accessRoleId: number, enabled: boolean) {
  const syncedRole = activity.syncedRoles.find((role) => role.role_id === discordRoleId);
  if (!syncedRole) return;
  const ids = new Set(syncedRole.access_roles.map((role) => role.id));
  if (enabled) {
    ids.add(accessRoleId);
  } else {
    ids.delete(accessRoleId);
  }
  await activity.saveSyncedRoleAssignments(discordRoleId, [...ids]);
}
</script>

<template>
  <section class="panel-section">
    <div class="section-heading role-panel-heading">
      <div>
        <span>Role Panels</span>
        <h2>Discord roles mapped to Activity roles.</h2>
        <p>Synced roles keep Discord permissions, while Activity roles define panel access.</p>
      </div>
      <button class="ghost-button" type="button" :disabled="activity.moduleLoading" @click="activity.syncRolesFromDiscord">
        <RefreshCcw :size="16" />
        Sync roles
      </button>
    </div>

    <div class="rbac-table-wrap">
      <table class="rbac-table role-assignment-table">
        <thead>
          <tr>
            <th>Discord role</th>
            <th v-for="accessRole in availableRoles" :key="accessRole.id">{{ accessRole.name }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="role in activity.syncedRoles" :key="role.role_id">
            <td>
              <strong>{{ role.name }}</strong>
              <span>{{ role.is_admin ? "Discord Administrator" : `permissions: ${role.permissions}` }}</span>
            </td>
            <td v-for="accessRole in availableRoles" :key="`${role.role_id}-${accessRole.id}`">
              <input
                type="checkbox"
                :checked="hasAssignment(role.role_id, accessRole.id)"
                @change="toggleAssignment(role.role_id, accessRole.id, ($event.target as HTMLInputElement).checked)"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
