<script setup lang="ts">
defineProps<{
  title: string;
  text: string;
}>();
</script>

<template>
  <div class="state-screen">
    <div class="loader-ring" aria-hidden="true"></div>
    <h1>{{ title }}</h1>
    <p>{{ text }}</p>
  </div>
</template>
