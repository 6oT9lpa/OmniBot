<script setup lang="ts">
import { LockKeyhole } from "@lucide/vue";

defineProps<{
  title?: string;
  text?: string;
  actionLabel?: string;
  busy?: boolean;
}>();

defineEmits<{
  action: [];
}>();
</script>

<template>
  <section class="no-access-state">
    <div class="state-icon"><LockKeyhole :size="22" /></div>
    <h2>{{ title || $t("access.no_module") }}</h2>
    <p>{{ text || $t("access.admin_can_grant") }}</p>
    <button v-if="actionLabel" class="primary-button" type="button" :disabled="busy" @click="$emit('action')">
      {{ busy ? $t("access.syncing") : actionLabel }}
    </button>
    <RouterLink class="secondary-link" to="/">{{ $t("access.back_to_omni") }}</RouterLink>
  </section>
</template>
