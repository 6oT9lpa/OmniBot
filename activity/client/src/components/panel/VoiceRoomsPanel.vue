<script setup lang="ts">
import VoiceRoomCard from "./VoiceRoomCard.vue";
import { useActivityStore } from "../../stores/activity.store";

const activity = useActivityStore();
</script>

<template>
  <section class="panel-section">
    <div class="section-heading">
      <span>{{ $t("voice.eyebrow") }}</span>
      <h2>{{ $t("voice.heading") }}</h2>
      <div>
        <p>{{ $t("voice.description") }}</p>
      </div>
    </div>

    <div class="voice-room-grid">
      <VoiceRoomCard v-for="room in activity.voiceRooms" :key="room.channel_id" :room="room" />
    </div>
  </section>
</template>
