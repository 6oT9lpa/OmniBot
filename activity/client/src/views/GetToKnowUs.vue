<script setup lang="ts">
import AboutModulePanel from "../components/landing/AboutModulePanel.vue";
import AboutPanel from "../components/landing/AboutPanel.vue";

const principles = [
  {
    title: "Control",
    text: "Admins keep the final say over roles, alerts, logs and publishing. The Activity makes decisions visible before they become Discord actions.",
  },
  {
    title: "Automation",
    text: "Repeated setup work moves into clean workflows instead of long command chains. Welcome messages, role panels and voice rooms can be maintained without memorizing syntax.",
  },
  {
    title: "Safety",
    text: "AI moderation is designed around local Ollama checks, so communities can reduce external data exposure. Sensitive actions still pass through backend permission checks.",
  },
  {
    title: "Creativity",
    text: "Creators and developers get focused spaces for alerts, Dev Blog updates and previews. The goal is to publish better updates with less operational noise.",
  },
];

const pillars = [
  "AI Moderation: local classification, review signals and admin visibility.",
  "Community Management: welcome flows, role panels, logs and clear access rules.",
  "Creator Ecosystem: Twitch, YouTube and Kick alerts shaped for stream communities.",
  "Developer Publishing: Dev Blog drafts, previews and controlled publishing paths.",
];

const facts = [
  { value: "8+", label: "core modules from moderation to voice rooms" },
  { value: "4", label: "role workspaces for users, creators, developers and admins" },
  { value: "1", label: "Activity surface instead of scattered command setup" },
];

const modules = [
  "Welcome",
  "Role Panels",
  "Creator Alerts",
  "Dev Blog",
  "AI Metrics",
  "Logs",
  "Server Stats",
  "Voice Rooms",
  "Health Status",
];

const modulePanels = [
  {
    title: "Dynamic Voice Rooms",
    text: "Temporary voice spaces stay tidy with owner controls, limits, lock states and cleanup when a room is empty.",
    rows: ["Owner controls", "Auto cleanup", "Transfer ready"],
    value: "12 rooms",
    label: "Voice",
  },
  {
    title: "Server Statistics",
    text: "Message trends, voice time and member movement become readable without exporting logs or scanning channels.",
    rows: ["Top channels", "Join trends", "Voice time"],
    value: "98.4%",
    label: "Insights",
  },
  {
    title: "Logging",
    text: "Edits, deletions, role changes and moderation actions land in an audit trail with retention controls.",
    rows: ["Message edits", "Role changes", "Moderation log"],
    value: "Live",
    label: "Audit",
  },
];
</script>

<template>
  <main class="public-page compact-public">
    <section class="about-hero">
      <div>
        <span class="eyebrow">Get to Know Us</span>
        <h1>OMNIBOT IS A CONTROL LAYER FOR COMMUNITIES.</h1>
      </div>
      <p>
        OmniBot began as a self-hosted alternative to paid, fragmented Discord bots.
        It is built for growing communities that need automation without losing control
        over data, roles and server decisions.
      </p>
    </section>

    <section class="about-grid">
      <AboutPanel
        eyebrow="Who we are"
        title="A practical toolkit for communities that outgrow command-only bots."
        text="OmniBot combines moderation, automation, creator tools and admin workflows in one Discord Activity. The public layer explains the product, while the panel gives each role a focused workspace."
      />
      <AboutPanel
        eyebrow="Architecture"
        title="Frontend -> Backend API -> Discord, DB and bot services."
        text="The browser never stores the bot token and never reaches Discord APIs directly. OAuth, permission checks and persistence stay behind the backend boundary."
      />
    </section>

    <section class="principle-grid" aria-label="What we stand for">
      <AboutPanel v-for="principle in principles" :key="principle.title" :eyebrow="principle.title" :text="principle.text" />
    </section>

    <section class="about-grid">
      <AboutPanel eyebrow="Product pillars" title="Four areas, one control surface.">
        <ul>
          <li v-for="pillar in pillars" :key="pillar">{{ pillar }}</li>
        </ul>
      </AboutPanel>
      <AboutPanel eyebrow="Facts">
        <div class="facts-grid">
          <div v-for="fact in facts" :key="fact.value">
            <strong>{{ fact.value }}</strong>
            <span>{{ fact.label }}</span>
          </div>
        </div>
      </AboutPanel>
    </section>

    <section class="about-module-grid" aria-label="Module previews">
      <AboutModulePanel
        v-for="panel in modulePanels"
        :key="panel.title"
        :title="panel.title"
        :text="panel.text"
        :rows="panel.rows"
        :value="panel.value"
        :label="panel.label"
      />
    </section>

    <section class="about-grid">
      <AboutPanel eyebrow="Role model" title="Access follows the person opening the Activity.">
        <ul>
          <li>Standard users see public information and allowed self-service modules.</li>
          <li>Creators can manage alert sources connected to their publishing workflow.</li>
          <li>Developers can prepare Dev Blog updates and technical announcements.</li>
          <li>Admins get the full control panel for configuration and audit work.</li>
        </ul>
      </AboutPanel>
      <AboutPanel eyebrow="Module map" title="Built to grow without adding clutter.">
        <p>
          Each module can become its own workspace while sharing the same navigation,
          permissions, loading states and API client.
        </p>
      </AboutPanel>
    </section>

    <section class="module-marquee" aria-label="Supported modules">
      <span v-for="module in modules" :key="module">{{ module }}</span>
    </section>
  </main>
</template>
