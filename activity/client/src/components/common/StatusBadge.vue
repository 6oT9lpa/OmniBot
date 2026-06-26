<script setup lang="ts">
defineProps<{
  tone?: "neutral" | "success" | "warning" | "danger";
  label: string;
}>();
</script>

<template>
  <span :class="['status-badge', tone || 'neutral']">{{ label }}</span>
</template>
