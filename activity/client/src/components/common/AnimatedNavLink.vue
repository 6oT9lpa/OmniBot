<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  to: string;
  label: string;
}>();

const letters = computed(() => Array.from(props.label));
</script>

<template>
  <RouterLink class="animated-nav-link" :to="to">
    <span
      v-for="(letter, index) in letters"
      :key="`${letter}-${index}`"
      class="animated-nav-link-letter"
      :style="{ transitionDelay: `${index * 22}ms` }"
    >
      {{ letter === " " ? "\u00a0" : letter }}
    </span>
  </RouterLink>
</template>
