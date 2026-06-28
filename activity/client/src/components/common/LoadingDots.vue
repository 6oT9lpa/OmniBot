<script setup lang="ts">
defineProps<{
  label?: string;
}>();
</script>

<template>
  <div class="loading-dots" role="status" :aria-label="label || 'Loading'">
    <span class="loading-dot dot-1"></span>
    <span class="loading-dot dot-2"></span>
    <span class="loading-dot dot-3"></span>
    <span class="loading-dot dot-4"></span>
  </div>
</template>
