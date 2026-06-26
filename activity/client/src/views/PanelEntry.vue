<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AccessMatrixTable from "../components/panel/AccessMatrixTable.vue";
import ActivityTimeline from "../components/panel/ActivityTimeline.vue";
import DiscordEmbedPreview from "../components/panel/DiscordEmbedPreview.vue";
import ModuleCard from "../components/panel/ModuleCard.vue";
import PanelSidebar from "../components/panel/PanelSidebar.vue";
import PanelTopbar from "../components/panel/PanelTopbar.vue";
import StatCard from "../components/panel/StatCard.vue";
import NoAccessState from "../components/common/NoAccessState.vue";
import StatusBadge from "../components/common/StatusBadge.vue";
import { useActivityStore } from "../stores/activity.store";
import {
  buildModules,
  dashboardMetrics,
  moduleLabels,
  moduleOrder,
  timelineEvents,
} from "../stores/mock-data";
import type { DashboardMetric, ModuleKey, WelcomeConfig } from "../types/activity.types";

const route = useRoute();
const router = useRouter();
const activity = useActivityStore();

const modules = computed(() => (activity.session ? buildModules(activity.session) : []));
const activeModule = computed<ModuleKey>(() => {
  const raw = route.params.module;
  const candidate = Array.isArray(raw) ? raw[0] : raw;
  return moduleOrder.includes(candidate as ModuleKey) ? (candidate as ModuleKey) : "dashboard";
});

const activeTitle = computed(() => moduleLabels[activeModule.value]);
const dashboardCards = computed<DashboardMetric[]>(() =>
  dashboardMetrics.map((metric) =>
    metric.label === "Bot latency"
      ? {
          ...metric,
          value: activity.botLatencyMs === null ? "Unavailable" : `${activity.botLatencyMs} ms`,
          delta: activity.healthLoading ? "Refreshing..." : activity.healthError || "Click health to refresh",
          tone: activity.healthError ? "warning" : metric.tone,
        }
      : metric,
  ),
);
const subtitle = computed(() =>
  activity.mode === "local"
    ? "Local preview. Discord OAuth starts automatically inside Activity."
    : `${activity.displayName} connected through Discord Activity.`,
);

const welcomeDraft = reactive<WelcomeConfig>({ ...activity.welcome });
const saving = reactive({ value: false, message: "" });

watch(
  () => activity.welcome,
  (next) => Object.assign(welcomeDraft, next),
  { deep: true },
);

watch(
  () => activeModule.value,
  (module) => {
    if (activity.session && !activity.can(module)) {
      void router.replace("/no-access");
    }
  },
  { immediate: true },
);

async function saveWelcome() {
  saving.value = true;
  saving.message = "Saving...";
  await activity.saveWelcome({ ...welcomeDraft });
  saving.value = false;
  saving.message = "Saved locally";
}

async function resetWelcome() {
  await activity.resetWelcome();
  Object.assign(welcomeDraft, activity.welcome);
  saving.message = "Reset complete";
}

async function refreshHealth() {
  await activity.refreshHealth();
}

function colorToHex(value: number) {
  return `#${value.toString(16).padStart(6, "0").slice(-6)}`;
}

function setColor(value: string) {
  welcomeDraft.color = parseInt(value.replace("#", ""), 16);
}
</script>

<template>
  <main class="panel-page">
    <PanelSidebar :modules="modules" :active-module="activeModule" />

    <section class="panel-workspace">
      <PanelTopbar :title="activeTitle" :subtitle="subtitle" />

      <div v-if="!activity.session" class="panel-content">
        <NoAccessState title="Session is loading" text="Omni is preparing the role-based workspace." />
      </div>

      <div v-else class="panel-content">
        <template v-if="activeModule === 'dashboard'">
          <section class="dashboard-hero">
            <div>
              <span class="eyebrow">Overview</span>
              <h2>Server operations at a glance.</h2>
              <p>
                A compact workspace for permissions, publishing, creator tools,
                AI signals and system health.
              </p>
            </div>
            <StatusBadge :label="activity.mode === 'local' ? 'local preview' : 'discord live'" tone="success" />
          </section>

          <section class="stats-grid">
            <StatCard v-for="metric in dashboardCards" :key="metric.label" :metric="metric" />
          </section>

          <section class="module-grid">
            <ModuleCard
              v-for="module in modules"
              :key="module.key"
              :module="module"
              :active="activeModule === module.key"
            />
          </section>

          <ActivityTimeline :events="timelineEvents" />
        </template>

        <template v-else-if="activeModule === 'access'">
          <section class="panel-section">
            <div class="section-heading">
              <span>Permission matrix</span>
              <h2>Role-based access that scales with every module.</h2>
              <p>
                This MVP keeps the UI ready for backend persistence. Real role IDs
                are still managed by the existing bot command and Activity API.
              </p>
            </div>
            <AccessMatrixTable />
          </section>
        </template>

        <template v-else-if="activeModule === 'welcome'">
          <section class="editor-grid">
            <form class="control-surface" @submit.prevent="saveWelcome">
              <div class="section-heading">
                <span>Welcome module</span>
                <h2>Design the first server moment.</h2>
              </div>

              <label class="toggle-row">
                <input v-model="welcomeDraft.is_enabled" type="checkbox" />
                <span>Enable welcome message</span>
              </label>

              <label>
                Title
                <input v-model="welcomeDraft.title" maxlength="256" />
              </label>

              <label>
                Description
                <textarea v-model="welcomeDraft.description" rows="7" maxlength="2000" />
              </label>

              <div class="form-grid">
                <label>
                  Color
                  <input type="color" :value="colorToHex(welcomeDraft.color)" @input="setColor(($event.target as HTMLInputElement).value)" />
                </label>
                <label>
                  Rules channel ID
                  <input v-model.number="welcomeDraft.rules_channel_id" inputmode="numeric" placeholder="Optional" />
                </label>
                <label>
                  Roles channel ID
                  <input v-model.number="welcomeDraft.roles_channel_id" inputmode="numeric" placeholder="Optional" />
                </label>
                <label>
                  Footer
                  <input v-model="welcomeDraft.footer_text" placeholder="OmniBot Activity" />
                </label>
              </div>

              <div class="variable-row">
                <span>{user}</span>
                <span>{server}</span>
                <span>{member_count}</span>
                <span>{joined_at}</span>
              </div>

              <div class="form-actions">
                <button class="primary-button" type="submit" :disabled="saving.value">Save</button>
                <button class="ghost-button" type="button" @click="resetWelcome">Reset</button>
                <small>{{ saving.message }}</small>
              </div>
            </form>

            <DiscordEmbedPreview :config="welcomeDraft" />
          </section>
        </template>

        <template v-else-if="activeModule === 'creator-alerts'">
          <section class="panel-section split-section">
            <div class="section-heading">
              <span>Creator workspace</span>
              <h2>Sources, templates and notification history.</h2>
              <p>Creators will only see their own sources. Administrators can manage every creator.</p>
            </div>
            <div class="source-list">
              <article v-for="source in ['Twitch stream', 'YouTube video', 'Kick future']" :key="source">
                <strong>{{ source }}</strong>
                <span>Template ready</span>
                <button class="ghost-button" type="button">Test</button>
              </article>
            </div>
          </section>
        </template>

        <template v-else-if="activeModule === 'dev-blog'">
          <section class="editor-grid">
            <form class="control-surface">
              <div class="section-heading">
                <span>Developer publishing</span>
                <h2>Compose a Dev Blog update.</h2>
              </div>
              <label>Title<input value="OmniBot Activity roadmap" /></label>
              <label>Description<textarea rows="8">A modular Activity shell is now ready for role-based workspaces, previews and API integration.</textarea></label>
              <label>Tags<input value="activity, api, ux" /></label>
              <div class="form-actions">
                <button class="primary-button" type="button">Save Draft</button>
                <button class="ghost-button" type="button">Send Test</button>
                <button class="ghost-button" type="button">Publish</button>
              </div>
            </form>
            <article class="discord-preview">
              <div class="discord-preview-header"><span>Dev Blog preview</span><strong>Draft</strong></div>
              <h3>OmniBot Activity roadmap</h3>
              <p>A modular Activity shell is now ready for role-based workspaces, previews and API integration.</p>
              <footer><span>#activity #api #ux</span><span>Publish-ready</span></footer>
            </article>
          </section>
        </template>

        <template v-else-if="activeModule === 'health' || activeModule === 'integrations'">
          <section class="health-grid">
            <article
              v-for="signal in activity.healthSignals"
              :key="signal.name"
              :class="['health-card', signal.status, { refreshing: activity.healthLoading }]"
              role="button"
              tabindex="0"
              @click="refreshHealth"
              @keydown.enter.prevent="refreshHealth"
              @keydown.space.prevent="refreshHealth"
            >
              <span>{{ signal.name }}</span>
              <strong>{{ signal.value }}</strong>
              <small>{{ activity.healthLoading ? "refreshing" : signal.status }}</small>
            </article>
          </section>
        </template>

        <template v-else>
          <section class="panel-section">
            <div class="section-heading">
              <span>Module workspace</span>
              <h2>{{ activeTitle }} is scaffolded for the next integration pass.</h2>
              <p>
                The navigation, permission guard and module shell are ready. The next step
                is connecting this workspace to its repository/service/API implementation.
              </p>
            </div>
            <div class="empty-module">
              <strong>{{ activeTitle }}</strong>
              <span>Ready for API endpoints, validation and Discord preview wiring.</span>
            </div>
          </section>
        </template>
      </div>
    </section>
  </main>
</template>
