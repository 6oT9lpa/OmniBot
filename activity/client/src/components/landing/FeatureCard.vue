<script setup lang="ts">
defineProps<{
  index: string;
  title: string;
  text: string;
}>();
</script>

<template>
  <article class="feature-card">
    <span>{{ index }}</span>
    <h3>{{ title }}</h3>
    <p>{{ text }}</p>
  </article>
</template>
