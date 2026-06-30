<script setup lang="ts">
import { computed, reactive } from "vue";
import { useActivityStore } from "../../stores/activity.store";
import type { VoiceRoom } from "../../types/activity.types";

const props = defineProps<{
  room: VoiceRoom;
}>();

const activity = useActivityStore();
const draft = reactive({
  name: props.room.discord?.name || props.room.name,
  userLimit: props.room.discord?.user_limit ?? 0,
  adminId: props.room.admin_id || "",
  targetUserId: "",
  region: props.room.discord?.rtc_region || "",
});

const voiceMembers = computed(() => {
  const ids = new Set((props.room.voice_member_ids || []).map(String));
  return activity.members.filter((member) => ids.has(member.id) && member.id !== props.room.owner_id);
});
const currentUserId = computed(() => activity.session?.user.id || "");
const isOwner = computed(() => currentUserId.value === String(props.room.owner_id));
const isAdmin = computed(() => currentUserId.value === String(props.room.admin_id || ""));
const hasAdmin = computed(() => Boolean(props.room.admin_id));
const isCurrentVoiceMember = computed(() => (props.room.voice_member_ids || []).map(String).includes(currentUserId.value));
const actionMembers = computed(() => {
  const ids = new Set((props.room.voice_member_ids || []).map(String));
  return activity.members.filter((member) => {
    if (!ids.has(member.id) || member.id === currentUserId.value) return false;
    if (isAdmin.value && member.id === props.room.owner_id) return false;
    return true;
  });
});

function memberName(id?: string | null) {
  if (!id) return "Free";
  const member = activity.members.find((item) => item.id === String(id));
  return member ? member.display_name : String(id);
}

function isLocked(room: VoiceRoom) {
  return Boolean(
    room.discord?.permission_overwrites?.some((overwrite) => {
      const item = overwrite as Record<string, unknown>;
      return item.id === String(room.guild_id) && Boolean(Number(item.deny || 0) & 0x00100000);
    }),
  );
}

async function updateRoomName() {
  await activity.updateVoice(props.room.channel_id, { name: draft.name });
}

async function updateRoomLimit() {
  await activity.updateVoice(props.room.channel_id, { user_limit: Number(draft.userLimit) });
}

async function updateRoomRegion() {
  await activity.updateVoice(props.room.channel_id, { rtc_region: draft.region || null });
}

async function assignAdmin() {
  await activity.updateVoice(props.room.channel_id, { admin_id: draft.adminId || null });
}

async function clearAdmin() {
  draft.adminId = "";
  if (isAdmin.value && !isOwner.value) {
    await activity.updateVoice(props.room.channel_id, { release_admin: true });
    return;
  }
  await activity.updateVoice(props.room.channel_id, { admin_id: null });
}

async function takeAdmin() {
  await activity.updateVoice(props.room.channel_id, { claim_admin: true });
}

async function memberAction(key: "invite_user_id" | "kick_user_id" | "ban_user_id") {
  if (!draft.targetUserId) return;
  await activity.updateVoice(props.room.channel_id, { [key]: draft.targetUserId });
}
</script>

<template>
  <article class="voice-room-card">
    <div class="voice-room-head">
      <div>
        <strong>{{ room.discord?.name || room.name }}</strong>
        <span>Owner {{ memberName(room.owner_id) }} - Admin {{ memberName(room.admin_id) }}</span>
      </div>
      <span :class="['status-badge', isLocked(room) ? 'warning' : 'success']">
        {{ isLocked(room) ? "locked" : "open" }}
      </span>
    </div>

    <div class="voice-control-grid">
      <label>
        Name
        <input v-model="draft.name" maxlength="100" @change="updateRoomName" />
      </label>
      <label>
        Limit
        <input v-model.number="draft.userLimit" type="number" min="0" max="99" @change="updateRoomLimit" />
      </label>
      <label>
        Owner
        <select :value="room.owner_id" disabled>
          <option :value="room.owner_id">{{ memberName(room.owner_id) }}</option>
        </select>
      </label>
      <label v-if="isOwner && !hasAdmin">
        Admin
        <select v-model="draft.adminId" @change="assignAdmin">
          <option value="">Free</option>
          <option
            v-for="member in voiceMembers"
            :key="member.id"
            :value="member.id"
          >
            {{ member.display_name }}
          </option>
          <option v-if="voiceMembers.length === 0" value="" disabled>No users in room</option>
        </select>
      </label>
      <label>
        Region
        <select v-model="draft.region" @change="updateRoomRegion">
          <option value="">Automatic</option>
          <option value="rotterdam">Rotterdam</option>
          <option value="us-east">US East</option>
          <option value="us-west">US West</option>
          <option value="us-central">US Central</option>
          <option value="us-south">US South</option>
          <option value="singapore">Singapore</option>
          <option value="japan">Japan</option>
          <option value="brazil">Brazil</option>
          <option value="sydney">Sydney</option>
        </select>
      </label>
    </div>

    <div class="inline-actions">
      <button class="ghost-button compact" type="button" @click="activity.updateVoice(room.channel_id, { locked: true })">Lock</button>
      <button class="ghost-button compact" type="button" @click="activity.updateVoice(room.channel_id, { locked: false })">Unlock</button>
      <button v-if="!hasAdmin && isCurrentVoiceMember && !isOwner" class="ghost-button compact" type="button" @click="takeAdmin">Take admin</button>
      <button v-if="hasAdmin && (isOwner || isAdmin)" class="ghost-button compact" type="button" @click="clearAdmin">Clear admin</button>
      <button class="ghost-button danger compact" type="button" @click="activity.deleteVoice(room.channel_id)">Delete</button>
    </div>

    <div class="voice-member-actions">
      <select v-model="draft.targetUserId" aria-label="Target user">
        <option value="">Target user</option>
        <option v-for="member in actionMembers" :key="member.id" :value="member.id">
          {{ member.display_name }}
        </option>
        <option v-if="actionMembers.length === 0" value="" disabled>No users in room</option>
      </select>
      <button class="ghost-button compact" type="button" @click="memberAction('invite_user_id')">Invite</button>
      <button class="ghost-button compact" type="button" @click="memberAction('kick_user_id')">Kick</button>
      <button class="ghost-button danger compact" type="button" @click="memberAction('ban_user_id')">Ban</button>
    </div>
  </article>
</template>
