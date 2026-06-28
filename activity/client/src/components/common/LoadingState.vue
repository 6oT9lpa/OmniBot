<script setup lang="ts">
import LoadingDots from "./LoadingDots.vue";

defineProps<{
  title: string;
  text: string;
}>();
</script>

<template>
  <div class="state-screen">
    <LoadingDots :label="title" />
    <h1>{{ title }}</h1>
    <p>{{ text }}</p>
  </div>
</template>
