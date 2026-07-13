<script setup lang="ts">
import { accessMatrix, moduleLabel, moduleOrder } from "../../stores/mock-data";
</script>

<template>
  <div class="matrix-wrap">
    <table class="access-matrix">
      <thead>
        <tr>
          <th>{{ $t("common.role") }}</th>
          <th v-for="module in moduleOrder.slice(1, 8)" :key="module">{{ moduleLabel(module) }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in accessMatrix" :key="row.role">
          <th>{{ $t(`permission.${row.role}`) }}</th>
          <td v-for="module in moduleOrder.slice(1, 8)" :key="module">
            <span :class="['permission-pill', row.permissions[module]]">
              {{ $t(`permission.${row.permissions[module]}`) }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
