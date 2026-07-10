<script setup lang="ts">
import { computed, ref, watch } from "vue";
import RevealOnScroll from "../common/RevealOnScroll.vue";
import { useActivityStore } from "../../stores/activity.store";

const activity = useActivityStore();
const activeTab = ref<"channels" | "policy" | "blacklist" | "domains" | "actions" | "risk">("channels");
const selectedChannels = ref<string[]>([]);
const blacklist = ref("");
const domains = ref("");
const labelPolicy = ref('{\n  "TOXIC": { "risk_threshold": 45, "min_action": "LOG", "max_action": "WARN" }\n}');
const status = ref("");
const settings = computed(() => activity.aiModerator);
const tabs = [
  ["channels", "Channels"], ["policy", "Policy"], ["blacklist", "Blacklist"],
  ["domains", "Domains"], ["actions", "Action limits"], ["risk", "Risk"],
] as const;

watch(settings, (value) => {
  selectedChannels.value = value?.channels ?? [];
  blacklist.value = Array.isArray(value?.policy.blacklist_words) ? value!.policy.blacklist_words.join(", ") : "";
  domains.value = Array.isArray(value?.policy.allowed_domains) ? value!.policy.allowed_domains.join(", ") : "";
  if (value?.policy.labels) labelPolicy.value = JSON.stringify(value.policy.labels, null, 2);
}, { immediate: true });

async function saveChannels() {
  await activity.saveAiModeratorChannelValues(selectedChannels.value);
  status.value = "Moderated channels saved.";
}

async function savePolicy() {
  let labels: Record<string, unknown> = {};
  try { labels = JSON.parse(labelPolicy.value); } catch { status.value = "Label policy must be valid JSON."; return; }
  await activity.saveAiModeratorPolicyValue({
    blacklist_words: split(blacklist.value), allowed_domains: split(domains.value), labels,
  });
  status.value = "AI moderation policy saved.";
}

function split(value: string) { return value.split(",").map((item) => item.trim()).filter(Boolean).slice(0, 200); }
</script>

<template>
  <RevealOnScroll tag="section" class="panel-section">
    <div class="section-heading">
      <span>AI Moderator</span>
      <h2>Local AI moderation settings.</h2>
      <div><p>Choose the channels sent to the local moderator and configure per-label risk and action boundaries.</p></div>
    </div>
    <nav class="panel-nav ai-moderator-tabs" aria-label="AI moderation settings">
      <button v-for="[key, label] in tabs" :key="key" type="button" :class="{ active: activeTab === key }" @click="activeTab = key">{{ label }}</button>
    </nav>
  </RevealOnScroll>

  <RevealOnScroll tag="section" class="panel-section" :delay="60">
    <template v-if="activeTab === 'channels'">
      <h3>Moderated channels</h3>
      <p>Select every text channel that should be sent to AI moderation. The AI decision log is configured through <code>/set_channel</code> → <code>ai_moderation_log</code>.</p>
      <label v-for="channel in settings?.available_channels ?? []" :key="channel.id" class="toggle-row">
        <input v-model="selectedChannels" type="checkbox" :value="channel.id" /> <span>#{{ channel.name }}</span>
      </label>
      <button class="primary-button" type="button" @click="saveChannels">Save channels</button>
    </template>
    <template v-else-if="activeTab === 'blacklist'">
      <h3>Blacklist words</h3><p>Comma-separated terms; they are stored per server for the moderation policy.</p>
      <textarea v-model="blacklist" rows="6" maxlength="4000" />
      <button class="primary-button" type="button" @click="savePolicy">Save blacklist</button>
    </template>
    <template v-else-if="activeTab === 'domains'">
      <h3>Domains</h3><p>Comma-separated allowed domains for local policy review.</p>
      <textarea v-model="domains" rows="6" maxlength="4000" />
      <button class="primary-button" type="button" @click="savePolicy">Save domains</button>
    </template>
    <template v-else>
      <h3>{{ activeTab === 'risk' ? 'Risk thresholds' : activeTab === 'actions' ? 'Minimum and maximum actions' : 'Label policy' }}</h3>
      <p>Configure each label with <code>risk_threshold</code>, <code>min_action</code> and <code>max_action</code>. Supported plans include LOG, REVIEW, WARN, DELETE, TIMEOUT and BAN.</p>
      <textarea v-model="labelPolicy" rows="14" maxlength="12000" />
      <button class="primary-button" type="button" @click="savePolicy">Save label policy</button>
    </template>
    <small>{{ status }}</small>
  </RevealOnScroll>
</template>
