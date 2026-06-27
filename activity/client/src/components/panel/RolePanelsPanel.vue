<script setup lang="ts">
import { computed } from "vue";
import { Plus, RefreshCcw, X } from "@lucide/vue";
import { useActivityStore } from "../../stores/activity.store";

const activity = useActivityStore();
const availableRoles = computed(() => activity.accessRoles);

async function addAssignment(discordRoleId: string, accessRoleId: string) {
  if (!accessRoleId) return;
  const syncedRole = activity.syncedRoles.find((role) => role.role_id === discordRoleId);
  if (!syncedRole) return;
  const ids = new Set(syncedRole.access_roles.map((role) => role.id));
  ids.add(Number(accessRoleId));
  await activity.saveSyncedRoleAssignments(discordRoleId, [...ids]);
}

async function removeAssignment(discordRoleId: string, accessRoleId: number) {
  const syncedRole = activity.syncedRoles.find((role) => role.role_id === discordRoleId);
  if (!syncedRole) return;
  await activity.saveSyncedRoleAssignments(
    discordRoleId,
    syncedRole.access_roles.filter((role) => role.id !== accessRoleId).map((role) => role.id),
  );
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

    <div class="role-map-list">
      <article v-for="role in activity.syncedRoles" :key="role.role_id" class="role-map-row">
        <div class="role-main">
          <strong>{{ role.name }}</strong>
          <span>{{ role.is_admin ? "Discord Administrator" : `permissions: ${role.permissions}` }}</span>
        </div>
        <div class="role-chip-row">
          <button
            v-for="accessRole in role.access_roles"
            :key="accessRole.id"
            class="role-chip"
            type="button"
            @click="removeAssignment(role.role_id, accessRole.id)"
          >
            {{ accessRole.name }}
            <X :size="13" />
          </button>
          <label class="role-add">
            <Plus :size="16" />
            <select @change="addAssignment(role.role_id, ($event.target as HTMLSelectElement).value); ($event.target as HTMLSelectElement).value = ''">
              <option value="">Add</option>
              <option v-for="accessRole in availableRoles" :key="accessRole.id" :value="accessRole.id">
                {{ accessRole.name }}
              </option>
            </select>
          </label>
        </div>
      </article>
    </div>
  </section>
</template>
