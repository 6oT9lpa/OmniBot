<script setup lang="ts">
import { computed, ref } from "vue";
import { Plus, Save } from "@lucide/vue";
import { useActivityStore } from "../../stores/activity.store";
import { moduleLabels, moduleOrder } from "../../stores/mock-data";
import type { ModuleKey, PermissionLevel } from "../../types/activity.types";

const activity = useActivityStore();
const newRoleName = ref("");
const permissionOptions: PermissionLevel[] = ["disabled", "view", "edit", "publish", "manage"];
const visibleModules = computed(() => moduleOrder);

async function createRole() {
  if (!newRoleName.value.trim()) return;
  await activity.createAccessRole(newRoleName.value);
  newRoleName.value = "";
}

async function saveRole(roleId: number, modules: Record<ModuleKey, PermissionLevel>) {
  await activity.saveAccessRoleModules(roleId, modules);
}
</script>

<template>
  <section class="panel-section">
    <div class="section-heading">
      <span>Access Control</span>
      <h2>Activity roles decide which tabs each user can see.</h2>
      <p>Configure universal roles or add a unique role for this server.</p>
    </div>

    <form class="module-toolbar" @submit.prevent="createRole">
      <input v-model="newRoleName" placeholder="Unique Activity role name" />
      <button class="primary-button" type="submit">
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
            <th>Save</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="role in activity.accessRoles" :key="role.id">
            <td>
              <strong>{{ role.name }}</strong>
              <span>{{ role.is_builtin ? "universal" : "custom" }}</span>
            </td>
            <td v-for="module in visibleModules" :key="`${role.id}-${module}`">
              <select v-model="role.modules[module]">
                <option v-for="option in permissionOptions" :key="option" :value="option">{{ option }}</option>
              </select>
            </td>
            <td>
              <button class="icon-button" type="button" title="Save permissions" @click="saveRole(role.id, role.modules)">
                <Save :size="16" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
