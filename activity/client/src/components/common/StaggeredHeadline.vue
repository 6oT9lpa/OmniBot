<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    text: string;
    as?: string;
  }>(),
  {
    as: "h1",
  },
);

const characters = computed(() => Array.from(props.text));
</script>

<template>
  <component :is="props.as" class="staggered-headline" :aria-label="props.text">
    <span
      v-for="(character, index) in characters"
      :key="`${character}-${index}`"
      class="staggered-letter"
      :class="{ 'is-space': character === ' ' }"
      :style="{ '--letter-index': index }"
      aria-hidden="true"
    >
      {{ character === " " ? "\u00A0" : character }}
    </span>
  </component>
</template>
