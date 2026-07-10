<script setup lang="ts">
import { Bot, BrainCircuit, Database, RadioTower, ServerCog, ShieldCheck } from "@lucide/vue";
import RevealOnScroll from "../components/common/RevealOnScroll.vue";
import FeatureCard from "../components/landing/FeatureCard.vue";
import HeroText from "../components/landing/HeroText.vue";

const features = [
  {
    index: "01",
    title: "Moderation With AI Signals",
    text: "Classic moderation commands, logs, punishment history and local AI Moderator checks help staff react faster while keeping humans in control.",
  },
  {
    index: "02",
    title: "Creator & Developer Tools",
    text: "Stream alerts, video notifications, Dev Blog publishing and embed builders help creators and developers share updates beautifully.",
  },
  {
    index: "03",
    title: "Activity Control Surface",
    text: "Dashboard, bot settings, integrations, health checks, statistics and access rules live in one focused Discord Activity.",
  },
  {
    index: "04",
    title: "Dynamic Voice Rooms",
    text: "Temporary voice channels with owner controls for naming, user limits, lock states and ownership transfer, with cleanup when rooms go empty.",
  },
  {
    index: "05",
    title: "Server Statistics & Insights",
    text: "Track message activity, voice time, top members, channel trends and member movement in one clear dashboard.",
  },
  {
    index: "06",
    title: "Logging & Audit Trail",
    text: "Message edits, deletions, role changes and moderation actions are logged with configurable retention for transparent admin history.",
  },
];

const aiCapabilities = [
  {
    icon: ShieldCheck,
    title: "Signals before punishment",
    text: "AI Moderator returns labels, risk score, confidence, reasons and recommended actions. Staff policy still defines what can happen next.",
  },
  {
    icon: BrainCircuit,
    title: "Local ruBERT model",
    text: "The moderation API can load the trained ruBERT tiny2 model locally and use CUDA on the server when NVIDIA drivers are available.",
  },
  {
    icon: ServerCog,
    title: "Activity controlled",
    text: "Admins choose covered channels, blacklist words, allowed domains, label thresholds and maximum action levels from the Activity panel.",
  },
  {
    icon: Database,
    title: "Audit friendly",
    text: "Health checks, policy decisions and moderation metadata stay visible for troubleshooting, review and safer iteration.",
  },
];
</script>

<template>
  <main class="public-page">
    <RevealOnScroll>
      <HeroText
        kicker="OmniBot Activity"
        title="BE A PART OF SOMETHING MARVELLOUS"
        body="OmniBot is a modular Discord bot with a protected Activity panel, Creator Alerts, Dev Blog publishing, dynamic voice rooms, analytics and a local AI Moderator connected to the current production stack."
      />
    </RevealOnScroll>

    <section class="feature-grid" aria-label="Why Omni">
      <RevealOnScroll
        v-for="feature in features"
        :key="feature.index"
        :delay="Number(feature.index) * 45"
      >
        <FeatureCard
          :index="feature.index"
          :title="feature.title"
          :text="feature.text"
        />
      </RevealOnScroll>
    </section>

    <RevealOnScroll tag="section" class="ai-story-band">
      <div class="ai-story-copy">
        <span class="eyebrow">AI Moderator</span>
        <h2>Local moderation intelligence, controlled by your server rules.</h2>
        <p>
          OmniBot does not treat AI as a magic ban button. Selected Discord channels are
          sent to a local AI Moderator API, where rules, semantic checks, ruBERT
          classification, risk scoring and policy resolution work together. The result is
          a clear moderation signal that admins can tune from Activity.
        </p>
      </div>
      <div class="ai-story-grid" aria-label="AI Moderator capabilities">
        <article v-for="item in aiCapabilities" :key="item.title">
          <component :is="item.icon" :size="22" />
          <div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.text }}</p>
          </div>
        </article>
      </div>
    </RevealOnScroll>

    <RevealOnScroll tag="section" class="showcase-band">
      <div class="showcase-copy">
        <span class="eyebrow">Current production stack</span>
        <h2>One Activity. Many workspaces. Local AI checks.</h2>
        <p>
          Every module, from roles and logs to stream alerts, Dev Blog posts and AI
          moderation, lives in one dashboard instead of scattered commands. Admins see
          what changed, who has access, which services are healthy and what needs review
          without digging through channel history.
        </p>
      </div>
      <div class="showcase-stack" aria-hidden="true">
        <div><ShieldCheck :size="20" /> Permission Matrix</div>
        <div><RadioTower :size="20" /> Creator Alerts</div>
        <div><Bot :size="20" /> Local AI Moderator</div>
      </div>
    </RevealOnScroll>
  </main>
</template>
