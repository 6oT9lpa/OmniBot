<script setup lang="ts">
import { accessMatrix, moduleLabels, moduleOrder } from "../../stores/mock-data";
</script>

<template>
  <div class="matrix-wrap">
    <table class="access-matrix">
      <thead>
        <tr>
          <th>Role</th>
          <th v-for="module in moduleOrder.slice(1, 8)" :key="module">{{ moduleLabels[module] }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in accessMatrix" :key="row.role">
          <th>{{ row.role }}</th>
          <td v-for="module in moduleOrder.slice(1, 8)" :key="module">
            <span :class="['permission-pill', row.permissions[module]]">
              {{ row.permissions[module] }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
