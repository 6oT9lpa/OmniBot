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
      <span>{{ $t("module.role-panels") }}</span>
      <h2>{{ $t("roles.heading") }}</h2>
      <div>
        <p>{{ $t("roles.description") }}</p>
      </div>
      <button class="ghost-button" type="button" :disabled="activity.moduleLoading" @click="activity.syncRolesFromDiscord">
        <RefreshCcw :size="16" />
        {{ $t("settings.sync_roles") }}
      </button>
    </div>

    <div class="role-map-list">
      <article v-for="role in activity.syncedRoles" :key="role.role_id" class="role-map-row">
        <div class="role-main">
          <strong>{{ role.name }}</strong>
          <span>{{ role.is_admin ? $t("roles.discord_admin") : $t("roles.permissions", { value: role.permissions }) }}</span>
        </div>
        <div class="role-chip-row">
          <label v-for="accessRole in availableRoles" :key="`${role.role_id}-${accessRole.id}`" class="role-chip selectable">
            <input
              type="checkbox"
              :checked="hasAssignment(role.role_id, accessRole.id)"
              @change="toggleAssignment(role.role_id, accessRole.id, ($event.target as HTMLInputElement).checked)"
            />
            <span>{{ accessRole.name }}</span>
          </label>
        </div>
      </article>
    </div>
  </section>
</template>
