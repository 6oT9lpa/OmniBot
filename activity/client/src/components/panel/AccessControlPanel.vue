<script setup lang="ts">
import { computed, ref } from "vue";
import { Plus, X } from "@lucide/vue";
import { useActivityStore } from "../../stores/activity.store";
import { accessConfigurableModules, moduleLabels } from "../../stores/mock-data";
import type { ModuleKey, PermissionLevel } from "../../types/activity.types";

const activity = useActivityStore();
const newRoleName = ref("");
const savingRoleId = ref<number | null>(null);
const visibleModules = computed(() => accessConfigurableModules);
const visibleRoles = computed(() => activity.accessRoles);

async function addRole() {
  const name = newRoleName.value.trim();
  if (!name) return;
  await activity.createAccessRole(name);
  newRoleName.value = "";
}

async function deleteRole(roleId: number) {
  await activity.deleteAccessRole(roleId);
}

async function saveRoleAccess(roleId: number, modules: Record<ModuleKey, PermissionLevel>) {
  savingRoleId.value = roleId;
  try {
    await activity.saveAccessRoleModules(roleId, modules);
  } finally {
    savingRoleId.value = null;
  }
}

function accessValue(permission: PermissionLevel) {
  return permission === "disabled" ? "deny" : "access";
}

function setAccessValue(roleId: number, modules: Record<ModuleKey, PermissionLevel>, module: ModuleKey, value: string) {
  modules[module] = value === "access" ? "view" : "disabled";
  void saveRoleAccess(roleId, modules);
}
</script>

<template>
  <section class="panel-section">
    <div class="section-heading">
      <span>Access Roles</span>
      <h2>Activity roles decide which tabs each user can see.</h2>
      <p>Add custom Activity roles, remove unused ones and choose which tabs are visible.</p>
    </div>

    <form class="module-toolbar" @submit.prevent="addRole">
      <input v-model="newRoleName" maxlength="48" placeholder="Unique role name" />
      <button class="primary-button" type="submit" :disabled="!newRoleName.trim() || activity.moduleLoading">
        <Plus :size="16" />
        Add role
      </button>
    </form>

    <div class="rbac-table-wrap">
      <table class="rbac-table">
        <thead>
          <tr>
            <th>Activity role</th>
            <th v-for="module in visibleModules" :key="module">{{ moduleLabels[module] }}</th>
            <th>Status</th>
            <th>Delete</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="role in visibleRoles" :key="role.id">
            <td>
              <strong>{{ role.name }}</strong>
              <span>{{ role.is_builtin ? "universal" : "custom" }}</span>
            </td>
            <td v-for="module in visibleModules" :key="`${role.id}-${module}`">
              <select
                :value="accessValue(role.modules[module])"
                :disabled="role.slug === 'administrator'"
                @change="setAccessValue(role.id, role.modules, module, ($event.target as HTMLSelectElement).value)"
              >
                <option value="access">access</option>
                <option value="deny">deny</option>
              </select>
            </td>
            <td>
              <span>{{ savingRoleId === role.id ? "saving" : "auto" }}</span>
            </td>
            <td>
              <button
                v-if="!role.is_builtin"
                class="icon-button danger"
                type="button"
                title="Delete role"
                @click="deleteRole(role.id)"
              >
                <X :size="16" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
