<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  kicker: string;
  title: string;
  body: string;
}>();

const words = computed(() => props.title.split(" "));
</script>

<template>
  <section class="hero-section">
    <div class="hero-copy">
      <span class="eyebrow">{{ kicker }}</span>
      <h1>
        <span v-for="(word, index) in words" :key="`${word}-${index}`" class="hero-word">
          {{ word }}{{ index < words.length - 1 ? " " : "" }}
        </span>
      </h1>
    </div>
    <p class="hero-body">{{ body }}</p>
  </section>
</template>
