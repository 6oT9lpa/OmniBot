<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    text: string;
    as?: string;
    speed?: number;
  }>(),
  {
    as: "h1",
    speed: 42,
  },
);

const characters = computed(() => Array.from(props.text));
const visibleCount = ref(0);
let timerId: number | undefined;

function clearTypingTimer() {
  if (timerId !== undefined) {
    window.clearInterval(timerId);
    timerId = undefined;
  }
}

function startTyping() {
  clearTypingTimer();
  visibleCount.value = 0;

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    visibleCount.value = characters.value.length;
    return;
  }

  timerId = window.setInterval(() => {
    visibleCount.value += 1;
    if (visibleCount.value >= characters.value.length) {
      visibleCount.value = characters.value.length;
      clearTypingTimer();
    }
  }, props.speed);
}

watch(() => props.text, startTyping);

onMounted(startTyping);
onBeforeUnmount(clearTypingTimer);
</script>

<template>
  <component :is="props.as" class="staggered-headline typewriter-headline" :aria-label="props.text">
    <span
      v-for="(character, index) in characters.slice(0, visibleCount)"
      :key="`${character}-${index}`"
      class="typewriter-letter"
      :class="{ 'is-space': character === ' ' }"
      aria-hidden="true"
    >
      {{ character === " " ? "\u00A0" : character }}
    </span>
    <span class="typewriter-cursor" aria-hidden="true"></span>
  </component>
</template>
