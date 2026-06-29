<script setup lang="ts">
import VoiceRoomCard from "./VoiceRoomCard.vue";
import { useActivityStore } from "../../stores/activity.store";

const activity = useActivityStore();
</script>

<template>
  <section class="panel-section">
    <div class="section-heading">
      <span>Dynamic voice</span>
      <h2>Bot-created rooms and controls.</h2>
      <div>
        <p>Manage room name, limit, lock state, temporary admin and member access from the Activity panel.</p>
      </div>
    </div>

    <div class="voice-room-grid">
      <VoiceRoomCard v-for="room in activity.voiceRooms" :key="room.channel_id" :room="room" />
    </div>
  </section>
</template>
