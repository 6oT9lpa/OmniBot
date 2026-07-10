<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { Check, Hash, Plus, ShieldCheck, Trash2 } from "@lucide/vue";
import RevealOnScroll from "../common/RevealOnScroll.vue";
import { useActivityStore } from "../../stores/activity.store";
import type { AiModerationAction, AiModerationLabelPolicy, AiModerationPolicy } from "../../types/activity.types";

type AiModeratorTab = "channels" | "policy" | "blacklist" | "domains" | "actions" | "risk";

type LabelDefinition = {
  key: string;
  title: string;
  description: string;
  defaultPolicy: AiModerationLabelPolicy;
};

const activity = useActivityStore();
const activeTab = ref<AiModeratorTab>("channels");
const selectedChannels = ref<string[]>([]);
const blacklistDraft = ref("");
const domainDraft = ref("");
const status = ref("");
const settings = computed(() => activity.aiModerator);
const actionOptions: Array<{ value: AiModerationAction; label: string }> = [
  { value: "IGNORE", label: "Ignore" },
  { value: "LOG", label: "Log only" },
  { value: "REVIEW", label: "Send for review" },
  { value: "WARN", label: "Warn member" },
  { value: "DELETE", label: "Delete message" },
  { value: "DELETE_WARN", label: "Delete and warn" },
  { value: "TIMEOUT", label: "Timeout member" },
  { value: "KICK", label: "Kick member" },
  { value: "BAN", label: "Ban member" },
];
const actionRank: Record<AiModerationAction, number> = Object.fromEntries(
  actionOptions.map((action, index) => [action.value, index]),
) as Record<AiModerationAction, number>;
const labelDefinitions: LabelDefinition[] = [
  { key: "SPAM", title: "Spam", description: "Repeated or automated messages.", defaultPolicy: policy(30, "LOG", "DELETE") },
  { key: "ADVERTISEMENT", title: "Advertising", description: "Unapproved promotion and self-advertising.", defaultPolicy: policy(25, "LOG", "DELETE") },
  { key: "INVITE", title: "Invite links", description: "Discord invites and unsolicited community links.", defaultPolicy: policy(20, "LOG", "DELETE") },
  { key: "SCAM", title: "Scam", description: "Fraud, phishing, or attempts to steal access.", defaultPolicy: policy(55, "DELETE_WARN", "BAN") },
  { key: "TOXIC", title: "Toxicity", description: "Hostile or disruptive language.", defaultPolicy: policy(45, "LOG", "WARN") },
  { key: "HATE", title: "Hate speech", description: "Content attacking protected groups.", defaultPolicy: policy(55, "WARN", "TIMEOUT") },
  { key: "THREAT", title: "Threats", description: "Threats of violence or harm.", defaultPolicy: policy(65, "DELETE_WARN", "BAN") },
  { key: "NSFW", title: "Adult content", description: "Sexual or explicit material.", defaultPolicy: policy(55, "DELETE", "TIMEOUT") },
  { key: "EVASION", title: "Filter evasion", description: "Attempts to bypass moderation rules.", defaultPolicy: policy(50, "WARN", "TIMEOUT") },
  { key: "FLOOD", title: "Flooding", description: "Excessive rapid messages.", defaultPolicy: policy(30, "LOG", "DELETE") },
  { key: "URL", title: "Links", description: "Suspicious or unapproved links.", defaultPolicy: policy(45, "REVIEW", "DELETE") },
  { key: "IMAGE_SCAM", title: "Image scam", description: "Fraudulent images or QR-code scams.", defaultPolicy: policy(55, "DELETE_WARN", "BAN") },
];
const tabs: Array<{ key: AiModeratorTab; label: string }> = [
  { key: "channels", label: "Channels" },
  { key: "policy", label: "Overview" },
  { key: "blacklist", label: "Blocked words" },
  { key: "domains", label: "Allowed domains" },
  { key: "actions", label: "Actions" },
  { key: "risk", label: "Risk" },
];
const moderationPolicy = reactive<AiModerationPolicy>(emptyPolicy());

watch(settings, (value) => {
  selectedChannels.value = visibleSelectedChannels(value?.channels ?? []);
  Object.assign(moderationPolicy, clonePolicy(value?.policy));
}, { immediate: true });

function policy(riskThreshold: number, minAction: AiModerationAction, maxAction: AiModerationAction): AiModerationLabelPolicy {
  return { risk_threshold: riskThreshold, min_action: minAction, max_action: maxAction };
}

function emptyPolicy(): AiModerationPolicy {
  return {
    blacklist_words: [],
    allowed_domains: [],
    labels: Object.fromEntries(labelDefinitions.map((item) => [item.key, { ...item.defaultPolicy }])),
    blacklist_action: "DELETE_WARN",
    unapproved_domain_action: "REVIEW",
  };
}

function clonePolicy(source: AiModerationPolicy | undefined): AiModerationPolicy {
  const defaults = emptyPolicy();
  if (!source) return defaults;
  return {
    blacklist_words: [...source.blacklist_words],
    allowed_domains: [...source.allowed_domains],
    labels: Object.fromEntries(labelDefinitions.map((item) => [item.key, { ...source.labels[item.key] ?? item.defaultPolicy }])),
    blacklist_action: source.blacklist_action,
    unapproved_domain_action: source.unapproved_domain_action,
  };
}

function tabLetters(label: string) {
  return Array.from(label);
}

function policyFor(label: string): AiModerationLabelPolicy {
  return moderationPolicy.labels[label];
}

function setMinimumAction(label: string, value: AiModerationAction) {
  const current = policyFor(label);
  current.min_action = value;
  if (actionRank[value] > actionRank[current.max_action]) current.max_action = value;
}

function setMaximumAction(label: string, value: AiModerationAction) {
  const current = policyFor(label);
  current.max_action = value;
  if (actionRank[value] < actionRank[current.min_action]) current.min_action = value;
}

async function saveChannels() {
  try {
    selectedChannels.value = visibleSelectedChannels(selectedChannels.value);
    await activity.saveAiModeratorChannelValues(selectedChannels.value);
    status.value = "Moderated channels saved.";
  } catch (error) {
    status.value = error instanceof Error ? error.message : "Could not save channels.";
  }
}

function visibleSelectedChannels(channelIds: string[]): string[] {
  const availableIds = new Set(settings.value?.available_channels.map((channel) => channel.id) ?? []);
  if (!availableIds.size) return channelIds;
  return channelIds.filter((channelId) => availableIds.has(channelId));
}

async function savePolicy(message: string) {
  try {
    await activity.saveAiModeratorPolicyValue(clonePolicy(moderationPolicy));
    status.value = message;
  } catch (error) {
    status.value = error instanceof Error ? error.message : "Could not save the policy.";
  }
}

function addBlacklistWords() {
  const values = splitValues(blacklistDraft.value);
  moderationPolicy.blacklist_words = unique([...moderationPolicy.blacklist_words, ...values]);
  blacklistDraft.value = "";
}

function addDomains() {
  const values = splitValues(domainDraft.value).map(normalizeDomain).filter(Boolean);
  moderationPolicy.allowed_domains = unique([...moderationPolicy.allowed_domains, ...values]);
  domainDraft.value = "";
}

function splitValues(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean).slice(0, 200);
}

function unique(values: string[]): string[] {
  return [...new Set(values.map((item) => item.toLocaleLowerCase()))].slice(0, 200);
}

function normalizeDomain(value: string): string {
  try {
    return new URL(value.includes("://") ? value : `https://${value}`).hostname.toLocaleLowerCase();
  } catch {
    return value.replace(/^www\./i, "").split("/")[0].toLocaleLowerCase();
  }
}

function removeValue(values: string[], value: string): string[] {
  return values.filter((item) => item !== value);
}
</script>

<template>
  <RevealOnScroll tag="section" class="panel-section ai-moderation-hero">
    <div class="section-heading">
      <span>AI moderation</span>
      <h2>Clear controls for a safer server.</h2>
      <div>
        <p>Choose which channels are checked, then tune the response for each type of content.</p>
      </div>
    </div>

    <nav class="ai-moderation-nav" aria-label="AI moderation settings">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ active: activeTab === tab.key }"
        :aria-current="activeTab === tab.key ? 'page' : undefined"
        @click="activeTab = tab.key"
      >
        <span
          v-for="(letter, index) in tabLetters(tab.label)"
          :key="`${tab.key}-${index}`"
          class="ai-moderation-nav-letter"
          :style="{ transitionDelay: `${index * 22}ms` }"
        >{{ letter === " " ? "\u00a0" : letter }}</span>
      </button>
    </nav>
  </RevealOnScroll>

  <RevealOnScroll tag="section" class="panel-section" :delay="60">
    <div v-if="activeTab === 'channels'" class="ai-moderation-workspace">
      <div class="ai-moderation-section-copy">
        <div>
          <span class="ai-moderation-kicker">Channel coverage</span>
          <h3>Moderated channels</h3>
          <p>Only selected text channels are sent to AI Moderator. Decisions can be sent to the configured AI moderation log channel.</p>
        </div>
        <span v-if="settings?.log_channel_id" class="ai-moderation-log-status"><Check :size="15" /> Log channel connected</span>
        <span v-else class="ai-moderation-log-status muted">Set the log channel in Bot Settings</span>
      </div>
      <div v-if="settings?.available_channels.length" class="ai-channel-grid">
        <label v-for="channel in settings.available_channels" :key="channel.id" class="ai-channel-card" :class="{ selected: selectedChannels.includes(channel.id) }">
          <input v-model="selectedChannels" type="checkbox" :value="channel.id" />
          <span class="ai-channel-icon"><Hash :size="18" /></span>
          <span class="ai-channel-copy"><strong>{{ channel.name }}</strong><small>{{ selectedChannels.includes(channel.id) ? "AI checks enabled" : "Not monitored" }}</small></span>
          <span class="ai-channel-check"><Check :size="16" /></span>
        </label>
      </div>
      <div v-else class="ai-empty-state"><Hash :size="22" /><span>No text channels were returned by Discord.</span></div>
      <div class="form-actions"><button class="primary-button" type="button" :disabled="activity.moduleLoading" @click="saveChannels">Save channels</button></div>
    </div>

    <div v-else-if="activeTab === 'policy'" class="ai-moderation-workspace">
      <div class="ai-moderation-section-copy">
        <div>
          <span class="ai-moderation-kicker">Server policy</span>
          <h3>{{ settings?.is_default_policy ? "Using the default policy" : "Custom policy is active" }}</h3>
          <p>{{ settings?.is_default_policy ? "The recommended policy is active for this server. It is saved to the database only after you make and save a change." : "This server has its own saved AI moderation policy." }}</p>
        </div>
        <ShieldCheck :size="32" class="ai-policy-icon" />
      </div>
      <div class="ai-policy-summary">
        <article><strong>{{ labelDefinitions.length }}</strong><span>content categories</span></article>
        <article><strong>{{ moderationPolicy.blacklist_words.length }}</strong><span>blocked words</span></article>
        <article><strong>{{ moderationPolicy.allowed_domains.length }}</strong><span>allowed domains</span></article>
      </div>
      <div class="ai-policy-controls">
        <label><span>When a blocked word is found</span><select v-model="moderationPolicy.blacklist_action"><option v-for="action in actionOptions" :key="action.value" :value="action.value">{{ action.label }}</option></select></label>
        <label><span>When a link is outside allowed domains</span><select v-model="moderationPolicy.unapproved_domain_action"><option v-for="action in actionOptions" :key="action.value" :value="action.value">{{ action.label }}</option></select></label>
      </div>
      <div class="form-actions"><button class="primary-button" type="button" :disabled="activity.moduleLoading" @click="savePolicy('Policy saved for this server.')">Save policy</button></div>
    </div>

    <div v-else-if="activeTab === 'blacklist'" class="ai-moderation-workspace">
      <div class="ai-moderation-section-copy"><div><span class="ai-moderation-kicker">Word filter</span><h3>Blocked words</h3><p>Add words or short phrases that should always trigger the action selected in Overview.</p></div></div>
      <div class="ai-token-input"><input v-model="blacklistDraft" maxlength="253" placeholder="Add a word or phrase" @keyup.enter.prevent="addBlacklistWords" /><button class="ghost-button" type="button" @click="addBlacklistWords"><Plus :size="16" /> Add</button></div>
      <div v-if="moderationPolicy.blacklist_words.length" class="ai-token-list"><span v-for="word in moderationPolicy.blacklist_words" :key="word" class="ai-token">{{ word }}<button type="button" :aria-label="`Remove ${word}`" @click="moderationPolicy.blacklist_words = removeValue(moderationPolicy.blacklist_words, word)"><Trash2 :size="14" /></button></span></div>
      <div v-else class="ai-empty-state"><ShieldCheck :size="22" /><span>No blocked words yet.</span></div>
      <div class="form-actions"><button class="primary-button" type="button" :disabled="activity.moduleLoading" @click="savePolicy('Blocked words saved.')">Save blocked words</button></div>
    </div>

    <div v-else-if="activeTab === 'domains'" class="ai-moderation-workspace">
      <div class="ai-moderation-section-copy"><div><span class="ai-moderation-kicker">Link rules</span><h3>Allowed domains</h3><p>Links outside this list follow the action selected in Overview. Subdomains are allowed automatically.</p></div></div>
      <div class="ai-token-input"><input v-model="domainDraft" maxlength="253" placeholder="example.com" @keyup.enter.prevent="addDomains" /><button class="ghost-button" type="button" @click="addDomains"><Plus :size="16" /> Add</button></div>
      <div v-if="moderationPolicy.allowed_domains.length" class="ai-token-list"><span v-for="domain in moderationPolicy.allowed_domains" :key="domain" class="ai-token">{{ domain }}<button type="button" :aria-label="`Remove ${domain}`" @click="moderationPolicy.allowed_domains = removeValue(moderationPolicy.allowed_domains, domain)"><Trash2 :size="14" /></button></span></div>
      <div v-else class="ai-empty-state"><Hash :size="22" /><span>All detected links are sent for review by default.</span></div>
      <div class="form-actions"><button class="primary-button" type="button" :disabled="activity.moduleLoading" @click="savePolicy('Allowed domains saved.')">Save allowed domains</button></div>
    </div>

    <div v-else-if="activeTab === 'actions'" class="ai-moderation-workspace">
      <div class="ai-moderation-section-copy"><div><span class="ai-moderation-kicker">Action boundaries</span><h3>Minimum and maximum actions</h3><p>Set the least and most severe action the bot may use for each content category.</p></div></div>
      <div class="ai-rule-list">
        <article v-for="label in labelDefinitions" :key="label.key" class="ai-rule-card"><div><strong>{{ label.title }}</strong><span>{{ label.description }}</span></div><label><span>At least</span><select :value="policyFor(label.key).min_action" @change="setMinimumAction(label.key, ($event.target as HTMLSelectElement).value as AiModerationAction)"><option v-for="action in actionOptions" :key="action.value" :value="action.value">{{ action.label }}</option></select></label><label><span>At most</span><select :value="policyFor(label.key).max_action" @change="setMaximumAction(label.key, ($event.target as HTMLSelectElement).value as AiModerationAction)"><option v-for="action in actionOptions" :key="action.value" :value="action.value">{{ action.label }}</option></select></label></article>
      </div>
      <div class="form-actions"><button class="primary-button" type="button" :disabled="activity.moduleLoading" @click="savePolicy('Action limits saved.')">Save action limits</button></div>
    </div>

    <div v-else class="ai-moderation-workspace">
      <div class="ai-moderation-section-copy"><div><span class="ai-moderation-kicker">Sensitivity</span><h3>Risk thresholds</h3><p>Below this score the category is only logged. Lower values make moderation more sensitive.</p></div></div>
      <div class="ai-risk-list">
        <label v-for="label in labelDefinitions" :key="label.key" class="ai-risk-card"><span><strong>{{ label.title }}</strong><small>{{ label.description }}</small></span><input v-model.number="policyFor(label.key).risk_threshold" type="range" min="0" max="100" step="1" /><output>{{ policyFor(label.key).risk_threshold }}</output></label>
      </div>
      <div class="form-actions"><button class="primary-button" type="button" :disabled="activity.moduleLoading" @click="savePolicy('Risk thresholds saved.')">Save risk thresholds</button></div>
    </div>

    <p v-if="status" class="ai-moderation-status" role="status">{{ status }}</p>
  </RevealOnScroll>
</template>
