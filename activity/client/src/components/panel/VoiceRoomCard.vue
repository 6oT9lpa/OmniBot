<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { useActivityStore } from "../../stores/activity.store";
import type { VoiceRoom } from "../../types/activity.types";
import { t } from "../../i18n";

const props = defineProps<{
  room: VoiceRoom;
}>();

const activity = useActivityStore();
type MemberAction = "invite" | "kick" | "ban";

const draft = reactive({
  name: props.room.discord?.name || props.room.name,
  userLimit: props.room.discord?.user_limit ?? 0,
  adminId: props.room.admin_id || "",
  targetUserId: "",
  region: props.room.discord?.rtc_region || "",
});
const activeMemberAction = ref<MemberAction | null>(null);

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
const inviteMembers = computed(() => activity.members.filter((member) => member.id !== currentUserId.value));
const activeTargetMembers = computed(() => (activeMemberAction.value === "invite" ? inviteMembers.value : actionMembers.value));

function memberName(id?: string | null) {
  if (!id) return t("voice.free");
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

function memberActionPayloadKey(action: MemberAction) {
  if (action === "invite") return "invite_user_id";
  if (action === "kick") return "kick_user_id";
  return "ban_user_id";
}

async function memberAction(action: MemberAction) {
  if (activeMemberAction.value !== action) {
    activeMemberAction.value = action;
    draft.targetUserId = "";
    return;
  }
  if (!draft.targetUserId) return;
  await activity.updateVoice(props.room.channel_id, { [memberActionPayloadKey(action)]: draft.targetUserId });
  activeMemberAction.value = null;
  draft.targetUserId = "";
}
</script>

<template>
  <article class="voice-room-card">
    <div class="voice-room-head">
      <div>
        <strong>{{ room.discord?.name || room.name }}</strong>
        <span>{{ $t("voice.owner") }} {{ memberName(room.owner_id) }} - {{ $t("voice.admin") }} {{ memberName(room.admin_id) }}</span>
      </div>
      <span :class="['status-badge', isLocked(room) ? 'warning' : 'success']">
        {{ $t(isLocked(room) ? "voice.locked" : "voice.open") }}
      </span>
    </div>

    <div class="voice-control-grid">
      <label>
        {{ $t("voice.name") }}
        <input v-model="draft.name" maxlength="100" @change="updateRoomName" />
      </label>
      <label>
        {{ $t("voice.limit") }}
        <input v-model.number="draft.userLimit" type="number" min="0" max="99" @change="updateRoomLimit" />
      </label>
      <label>
        {{ $t("voice.owner") }}
        <select :value="room.owner_id" disabled>
          <option :value="room.owner_id">{{ memberName(room.owner_id) }}</option>
        </select>
      </label>
      <label v-if="isOwner && !hasAdmin">
        {{ $t("voice.admin") }}
        <select v-model="draft.adminId" @change="assignAdmin">
          <option value="">{{ $t("voice.free") }}</option>
          <option
            v-for="member in voiceMembers"
            :key="member.id"
            :value="member.id"
          >
            {{ member.display_name }}
          </option>
          <option v-if="voiceMembers.length === 0" value="" disabled>{{ $t("voice.no_users_room") }}</option>
        </select>
      </label>
      <label>
        {{ $t("voice.region") }}
        <select v-model="draft.region" @change="updateRoomRegion">
          <option value="">{{ $t("voice.automatic") }}</option>
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
      <button class="ghost-button compact" type="button" @click="activity.updateVoice(room.channel_id, { locked: true })">{{ $t("voice.lock") }}</button>
      <button class="ghost-button compact" type="button" @click="activity.updateVoice(room.channel_id, { locked: false })">{{ $t("voice.unlock") }}</button>
      <button v-if="!hasAdmin && isCurrentVoiceMember && !isOwner" class="ghost-button compact" type="button" @click="takeAdmin">{{ $t("voice.take_admin") }}</button>
      <button v-if="hasAdmin && (isOwner || isAdmin)" class="ghost-button compact" type="button" @click="clearAdmin">{{ $t("voice.clear_admin") }}</button>
      <button class="ghost-button danger compact" type="button" @click="activity.deleteVoice(room.channel_id)">{{ $t("common.delete") }}</button>
    </div>

    <div :class="['voice-member-actions', { 'is-selecting': activeMemberAction }]">
      <TransitionGroup name="voice-action-button" tag="div" class="voice-action-button-row">
        <button
          v-if="!activeMemberAction || activeMemberAction === 'invite'"
          key="invite"
          :class="['ghost-button compact', { active: activeMemberAction === 'invite' }]"
          type="button"
          @click="memberAction('invite')"
        >
          {{ $t("voice.invite") }}
        </button>
        <button
          v-if="!activeMemberAction || activeMemberAction === 'kick'"
          key="kick"
          :class="['ghost-button compact', { active: activeMemberAction === 'kick' }]"
          type="button"
          @click="memberAction('kick')"
        >
          {{ $t("voice.kick") }}
        </button>
        <button
          v-if="!activeMemberAction || activeMemberAction === 'ban'"
          key="ban"
          :class="['ghost-button danger compact', { active: activeMemberAction === 'ban' }]"
          type="button"
          @click="memberAction('ban')"
        >
          {{ $t("voice.ban") }}
        </button>
      </TransitionGroup>

      <Transition name="voice-target-slide">
        <select v-if="activeMemberAction" v-model="draft.targetUserId" :aria-label="$t('voice.target_user')">
          <option value="" disabled>{{ $t("voice.target_user") }}</option>
          <option v-for="member in activeTargetMembers" :key="member.id" :value="member.id">
            {{ member.display_name }}
          </option>
          <option v-if="activeTargetMembers.length === 0" value="" disabled>
            {{ $t(activeMemberAction === "invite" ? "voice.no_users_server" : "voice.no_users_room") }}
          </option>
        </select>
      </Transition>
    </div>
  </article>
</template>
