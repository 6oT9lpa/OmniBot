<script setup lang="ts">
import { useActivityStore } from "../../stores/activity.store";

const activity = useActivityStore();
</script>

<template>
  <section class="panel-section">
    <div class="section-heading">
      <span>Dynamic voice</span>
      <h2>Bot-created rooms and controls.</h2>
    </div>
    <div class="record-list">
      <article v-for="room in activity.voiceRooms" :key="room.channel_id">
        <div>
          <strong>{{ room.discord?.name || room.name }}</strong>
          <span>Owner {{ room.owner_id }} · {{ room.is_persistent ? "persistent" : "temporary" }}</span>
        </div>
        <div class="inline-actions">
          <button class="ghost-button" type="button" @click="activity.updateVoice(room.channel_id, { locked: true })">Lock</button>
          <button class="ghost-button" type="button" @click="activity.updateVoice(room.channel_id, { locked: false })">Unlock</button>
          <button class="ghost-button" type="button" @click="activity.updateVoice(room.channel_id, { persistent: !room.is_persistent })">Persist</button>
          <button class="ghost-button danger" type="button" @click="activity.deleteVoice(room.channel_id)">Delete</button>
        </div>
      </article>
    </div>
  </section>
</template>
