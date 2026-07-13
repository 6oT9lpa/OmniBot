<script setup lang="ts">
import { Languages } from "@lucide/vue";
import { computed } from "vue";
import { useI18n } from "../../i18n";

const { locale, t, toggleLocale } = useI18n();
const nextLanguage = computed(() => t(locale.value === "en" ? "common.language.russian" : "common.language.english"));
const buttonLabel = computed(() => t("common.language.switch_to", { language: nextLanguage.value }));
</script>

<template>
  <button class="icon-button language-switcher" type="button" :title="buttonLabel" :aria-label="buttonLabel" @click="toggleLocale">
    <Languages :size="18" />
    <span aria-hidden="true">{{ locale.toUpperCase() }}</span>
  </button>
</template>
