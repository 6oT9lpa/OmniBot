<script setup lang="ts">
import { Moon, Sun } from "@lucide/vue";
import { useActivityStore } from "../../stores/activity.store";
import AnimatedNavLink from "./AnimatedNavLink.vue";

const activity = useActivityStore();
</script>

<template>
  <header class="app-header">
    <RouterLink class="wordmark" to="/" aria-label="Omni home">
      <img class="wordmark-logo" src="/omni-logo.png" alt="" />
      <span>
        <span class="wordmark-main">OMNI</span>
        <span class="wordmark-sub">discord bot</span>
      </span>
    </RouterLink>

    <nav class="public-nav" aria-label="Primary navigation">
      <AnimatedNavLink to="/" label="We are Omni" />
      <AnimatedNavLink to="/about" label="Get to Know Us" />
    </nav>

    <div class="header-actions">
      <button class="icon-button" type="button" title="Toggle theme" @click="activity.toggleTheme()">
        <Sun v-if="activity.theme === 'dark'" :size="18" />
        <Moon v-else :size="18" />
      </button>
      <RouterLink class="panel-cta" to="/panel">
        See Panel
      </RouterLink>
    </div>
  </header>
</template>
