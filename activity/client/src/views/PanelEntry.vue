<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AccessControlPanel from "../components/panel/AccessControlPanel.vue";
import AiModeratorPanel from "../components/panel/AiModeratorPanel.vue";
import BotSettingsPanel from "../components/panel/BotSettingsPanel.vue";
import CreatorAlertsPanel from "../components/panel/CreatorAlertsPanel.vue";
import DashboardPanel from "../components/panel/DashboardPanel.vue";
import DevBlogPanel from "../components/panel/DevBlogPanel.vue";
import HealthStatusPanel from "../components/panel/HealthStatusPanel.vue";
import IntegrationsPanel from "../components/panel/IntegrationsPanel.vue";
import LogsPanel from "../components/panel/LogsPanel.vue";
import PanelSidebar from "../components/panel/PanelSidebar.vue";
import PanelTopbar from "../components/panel/PanelTopbar.vue";
import RolePanelsPanel from "../components/panel/RolePanelsPanel.vue";
import ServerStatsPanel from "../components/panel/ServerStatsPanel.vue";
import VoiceRoomsPanel from "../components/panel/VoiceRoomsPanel.vue";
import WelcomeModulePanel from "../components/panel/WelcomeModulePanel.vue";
import LoadingDots from "../components/common/LoadingDots.vue";
import NoAccessState from "../components/common/NoAccessState.vue";
import { useActivityStore } from "../stores/activity.store";
import { buildModules, moduleLabels, moduleOrder } from "../stores/mock-data";
import type { ModuleKey } from "../types/activity.types";

const route = useRoute();
const router = useRouter();
const activity = useActivityStore();

const modules = computed(() =>
  activity.session ? buildModules(activity.session).filter((module) => module.permission !== "disabled") : [],
);
const activeModule = computed<ModuleKey>(() => {
  const raw = route.params.module;
  const candidate = Array.isArray(raw) ? raw[0] : raw;
  return moduleOrder.includes(candidate as ModuleKey) ? (candidate as ModuleKey) : "dashboard";
});

const activeTitle = computed(() => moduleLabels[activeModule.value]);
const subtitle = computed(() =>
  activity.session
    ? `${activity.displayName} connected through Discord Activity.`
    : "Discord Activity access is required.",
);
const sessionStateTitle = computed(() => {
  if (activity.accessError) return "Access denied";
  if (activity.error) return "Session failed";
  return "Session is loading";
});
const sessionStateText = computed(() =>
  activity.accessError?.message || activity.error || "Omni is preparing the role-based workspace.",
);
const sessionActionLabel = computed(() => {
  if (activity.accessError?.can_sync_roles) return "Sync roles";
  if (activity.error) return "Retry";
  return undefined;
});
const activeModuleLoaded = computed(() => Boolean(activity.loadedModules[activeModule.value]));
const activeModulePending = computed(() => activity.moduleLoading && !activeModuleLoaded.value);
const activeModuleFailed = computed(() => Boolean(activity.moduleError && !activeModuleLoaded.value));
const visibleError = computed(() => activity.moduleError || activity.healthError || activity.error);

function clearVisibleError() {
  activity.moduleError = null;
  activity.healthError = null;
  activity.error = null;
}

async function handleSessionAction() {
  if (activity.accessError?.can_sync_roles) {
    await activity.syncRolesFromDiscord();
    return;
  }
  activity.booted = false;
  await activity.boot();
}

async function retryActiveModule() {
  await activity.loadModuleData(activeModule.value);
}

watch(
  () => activeModule.value,
  (module) => {
    if (activity.session && !activity.can(module)) {
      void router.replace("/no-access");
      return;
    }
    void activity.loadModuleData(module);
  },
  { immediate: true },
);
</script>

<template>
  <main class="panel-page">
    <PanelSidebar :modules="modules" :active-module="activeModule" />

    <section class="panel-workspace">
      <PanelTopbar :title="activeTitle" :subtitle="subtitle" />
      <div v-if="visibleError && !activeModuleFailed" class="activity-error-banner" role="alert">
        <div>
          <strong>Request failed</strong>
          <span>{{ visibleError }}</span>
        </div>
        <button class="icon-button" type="button" aria-label="Dismiss error" @click="clearVisibleError">x</button>
      </div>

      <div v-if="!activity.session" class="panel-content">
        <NoAccessState
          :title="sessionStateTitle"
          :text="sessionStateText"
          :action-label="sessionActionLabel"
          :busy="activity.moduleLoading || activity.loading"
          @action="handleSessionAction"
        />
      </div>

      <div v-else-if="activeModulePending" class="panel-content module-loading-state">
        <LoadingDots :label="`Loading ${activeTitle}`" />
        <h2>{{ activeTitle }}</h2>
        <p>Loading module data from the server.</p>
      </div>

      <div v-else-if="activeModuleFailed" class="panel-content">
        <NoAccessState
          title="Module failed"
          :text="activity.moduleError || 'Module data could not be loaded.'"
          action-label="Retry"
          :busy="activity.moduleLoading"
          @action="retryActiveModule"
        />
      </div>

      <div v-else class="panel-content">
        <DashboardPanel v-if="activeModule === 'dashboard'" :modules="modules" :active-module="activeModule" />
        <AccessControlPanel v-else-if="activeModule === 'access'" />
        <WelcomeModulePanel v-else-if="activeModule === 'welcome'" />
        <RolePanelsPanel v-else-if="activeModule === 'role-panels'" />
        <CreatorAlertsPanel v-else-if="activeModule === 'creator-alerts'" />
        <AiModeratorPanel v-else-if="activeModule === 'ai-moderator'" />
        <DevBlogPanel v-else-if="activeModule === 'dev-blog'" />
        <VoiceRoomsPanel v-else-if="activeModule === 'voice-rooms'" />
        <ServerStatsPanel v-else-if="activeModule === 'server-stats'" />
        <LogsPanel v-else-if="activeModule === 'logs'" />
        <BotSettingsPanel v-else-if="activeModule === 'bot-settings'" />
        <IntegrationsPanel v-else-if="activeModule === 'integrations'" />
        <HealthStatusPanel v-else-if="activeModule === 'health'" />

        <section v-else class="panel-section">
          <div class="section-heading">
            <span>Module workspace</span>
            <h2>{{ activeTitle }} is scaffolded for the next integration pass.</h2>
            <div>
              <p>
                The navigation, permission guard and module shell are ready. The next step
                is connecting this workspace to its repository/service/API implementation.
              </p>
            </div>
          </div>
          <div class="empty-module">
            <strong>{{ activeTitle }}</strong>
            <span>Ready for API endpoints, validation and Discord preview wiring.</span>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>
